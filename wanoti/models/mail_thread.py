import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _register_hook(self):
        res = super()._register_hook()
        from odoo.addons.wanoti.controllers.checkout import patch_website_sale
        patch_website_sale()
        self._wanoti_patch_documents()
        return res

    def _wanoti_patch_documents(self):
        self._wanoti_wrap("stock.picking", "_action_done", "wanoti.mt_picking_done", "Transfer validated.")
        self._wanoti_wrap("pos.order", "action_pos_order_paid", "wanoti.mt_pos_paid", "Point of sale order paid.")

    def _wanoti_wrap(self, model_name, method_name, subtype_xmlid, body):
        if model_name not in self.env.registry:
            return
        model = self.env.registry[model_name]
        origin = getattr(model, method_name, None)
        if not origin or getattr(origin, "_wanoti_wrapped", False):
            return

        def wrapped(records, *args, **kwargs):
            result = origin(records, *args, **kwargs)
            subtype = records.env.ref(subtype_xmlid, raise_if_not_found=False)
            if subtype and records and not records.env.context.get("wanoti_skip"):
                for record in records:
                    try:
                        if hasattr(record, "message_post"):
                            record.with_context(mail_notify_noemail=True).message_post(
                                body=body,
                                subtype_id=subtype.id,
                            )
                        else:
                            message = records.env["mail.message"].sudo().create({
                                "model": record._name,
                                "res_id": record.id,
                                "body": body,
                                "subtype_id": subtype.id,
                                "message_type": "notification",
                            })
                            records.env["wanoti.dispatcher"].sudo()._enqueue(record, message)
                    except Exception:
                        _logger.exception("WaNoti could not queue %s", record)
            return result

        wrapped._wanoti_wrapped = True
        setattr(model, method_name, wrapped)

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        recipients = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
        if message and not self.env.context.get("wanoti_skip"):
            self.env["wanoti.dispatcher"]._enqueue(self, message)
        return recipients

    def _wanoti_customer_partners(self):
        """External partner on the document. Portal users count as customers."""
        self.ensure_one()
        partners = self.env["res.partner"]
        if "partner_id" in self._fields and self.partner_id and len(self.partner_id) == 1:
            partners |= self.partner_id
        return partners.filtered(
            lambda partner: not any(not user.share for user in partner.user_ids)
        )

    def _wanoti_staff_partners(self, message):
        """Assignee, subscribed internal followers, and internal users Odoo already notified."""
        self.ensure_one()
        partners = self.env["res.partner"]
        for field_name in ("user_id", "user_ids"):
            if field_name not in self._fields or not self[field_name]:
                continue
            users = self[field_name]
            if users._name == "res.users":
                partners |= users.partner_id
        if (
            "employee_id" in self._fields
            and self.employee_id
            and "user_id" in self.employee_id._fields
            and self.employee_id.user_id
        ):
            partners |= self.employee_id.user_id.partner_id
        subtype = message.subtype_id
        if subtype and "message_follower_ids" in self._fields:
            followers = self.message_follower_ids.filtered(
                lambda follower: subtype in follower.subtype_ids
            )
            partners |= followers.partner_id
        if message.notification_ids:
            partners |= message.notification_ids.res_partner_id
        return partners.filtered(
            lambda partner: any(not user.share for user in partner.user_ids)
        )

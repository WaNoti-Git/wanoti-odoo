from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _register_hook(self):
        res = super()._register_hook()
        from odoo.addons.wanoti.controllers.checkout import patch_website_sale
        patch_website_sale()
        return res

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

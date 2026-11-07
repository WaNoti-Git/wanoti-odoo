import logging

from odoo import _, api, models
from odoo import release
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

# Sale chatter events that already have a WaNoti template.
CUSTOMER_EVENTS = {
    "sale.mt_order_sent": "order_placed",
    "sale.mt_order_confirmed": "order_confirmed",
}
STAFF_EVENTS = {
    "sale.mt_order_sent": "admin_new_order",
    "sale.mt_order_confirmed": "admin_new_order",
}


class WanotiDispatcher(models.AbstractModel):
    _name = "wanoti.dispatcher"
    _description = "WaNoti WhatsApp sender"

    @api.model
    def _site_url(self):
        return (self.env["ir.config_parameter"].sudo().get_param("web.base.url") or "").rstrip("/")

    @api.model
    def _phone(self, partner):
        raw = partner.mobile or partner.phone or ""
        digits = "".join(ch for ch in raw if ch.isdigit())
        return digits if len(digits) >= 8 else ""

    @api.model
    def _company_of(self, record):
        if "company_id" in record._fields and record.company_id and len(record.company_id) == 1:
            return record.company_id
        return record.env.company

    @api.model
    def _selection_label(self, record, field_name):
        field = record._fields.get(field_name)
        if not field:
            return ""
        value = record[field_name]
        try:
            pairs = field._description_selection(record.env)
        except Exception:
            pairs = field.selection if isinstance(field.selection, (list, tuple)) else []
        return dict(pairs).get(value, value or "")

    @api.model
    def _tracking_text(self, message):
        lines = []
        for tracking in message.sudo().tracking_value_ids:
            label = tracking.field_id.field_description or tracking.field_id.name or ""
            old = getattr(tracking, "old_value_char", "") or getattr(tracking, "old_value_text", "") or ""
            new = getattr(tracking, "new_value_char", "") or getattr(tracking, "new_value_text", "") or ""
            if not old and not new:
                old = getattr(tracking, "old_value_integer", "") or getattr(tracking, "old_value_float", "") or ""
                new = getattr(tracking, "new_value_integer", "") or getattr(tracking, "new_value_float", "") or ""
            if old or new:
                lines.append("%s: %s → %s" % (label, old or "—", new or "—"))
        return "\n".join(lines)

    @api.model
    def _plain_body(self, message):
        body = html2plaintext(message.body or "").strip()
        tracking = self._tracking_text(message)
        if tracking:
            body = ("%s\n%s" % (body, tracking)).strip()
        return body[:1200]

    @api.model
    def _record_url(self, record):
        base = self._site_url()
        if not base or not record.id:
            return ""
        return "%s/web#id=%s&model=%s&view_type=form" % (base, record.id, record._name)

    @api.model
    def _generic_message(self, record, message, company):
        subtype = message.subtype_id
        parts = [
            "*%s*" % (company.name or "WaNoti"),
            "*%s: %s*" % (record._description or record._name, record.display_name or ""),
        ]
        if subtype and subtype.name:
            parts.append(subtype.name)
        author = message.author_id.name
        body = self._plain_body(message)
        if author and body:
            parts.append("%s: %s" % (author, body))
        elif body:
            parts.append(body)
        url = self._record_url(record)
        if url:
            parts.append(url)
        return "\n".join(part for part in parts if part)[:3500]

    @api.model
    def _event_for(self, record, subtype, role):
        if record._name != "sale.order" or not subtype:
            return "", False
        xmlid = subtype.get_external_id().get(subtype.id)
        event = (CUSTOMER_EVENTS if role == "customer" else STAFF_EVENTS).get(xmlid)
        return (event, True) if event else ("", False)

    @api.model
    def _sale_variables(self, order, company, site_url):
        lines = order.order_line
        if "display_type" in lines._fields:
            lines = lines.filtered(lambda line: not line.display_type)
        items = []
        for line in lines:
            items.append({
                "name": line.product_id.display_name or line.name or "",
                "qty": line.product_uom_qty,
                "price": "%s %s" % (line.price_subtotal, order.currency_id.name or ""),
            })
        partner = order.partner_id
        shipping = order.partner_shipping_id
        address = ", ".join(
            part for part in [
                shipping.street,
                shipping.street2,
                shipping.city,
                shipping.state_id.name,
                shipping.country_id.name,
            ] if part
        ) if shipping else ""
        date_order = order.date_order
        return {
            "customer_name": partner.name or "",
            "customer_phone": partner.mobile or partner.phone or "",
            "customer_email": partner.email or "",
            "order_id": order.name or "",
            "order_total": "%s %s" % (order.amount_total, order.currency_id.name or ""),
            "order_subtotal": "%s %s" % (order.amount_untaxed, order.currency_id.name or ""),
            "order_status": self._selection_label(order, "state"),
            "order_date": str(date_order.date()) if date_order else "",
            "shipping_address": address,
            "items_count": sum(lines.mapped("product_uom_qty")),
            "items": items,
            "site_name": company.name or "",
            "site_url": site_url,
            "order_admin_url": self._record_url(order),
            "support_email": company.email or "",
            "customer_note": html2plaintext(order.note or "").strip(),
        }

    @api.model
    def _enqueue(self, records, message):
        if not message or not message.model or message.model not in self.env or message.model.startswith("wanoti."):
            return
        payloads = []
        seen = set()
        for record in records:
            payloads.extend(self._payloads_for(record.sudo(), message.sudo(), seen))
        if not payloads:
            return
        dbname = self.env.cr.dbname

        def _run():
            try:
                from odoo.modules.registry import Registry
                from odoo import SUPERUSER_ID, api as odoo_api
                with Registry(dbname).cursor() as cr:
                    env = odoo_api.Environment(cr, SUPERUSER_ID, {"wanoti_skip": True})
                    env["wanoti.dispatcher"]._deliver(payloads)
                    cr.commit()
            except Exception:
                _logger.exception("WaNoti delivery failed")

        self.env.cr.postcommit.add(_run)

    @api.model
    def _payloads_for(self, record, message, seen):
        if not record or record._name != message.model or record.id != message.res_id:
            target = self.env[message.model].browse(message.res_id).exists() if message.model and message.res_id else record
            record = target.sudo() if target else record
        if not record or not record.exists():
            return []

        company = self._company_of(record)
        api_url = (company.wanoti_api_url or "").strip().rstrip("/")
        api_key = (company.wanoti_api_key or "").strip()
        if not api_url or not api_key or not company.wanoti_data_consent:
            return []

        subtype = message.subtype_id or self.env.ref("mail.mt_comment", raise_if_not_found=False)
        if not subtype:
            return []
        rule = self.env["wanoti.rule"].sudo().search([
            ("company_id", "=", company.id),
            ("model_id.model", "=", record._name),
            ("subtype_id", "=", subtype.id),
            "|",
            ("notify_customer", "=", True),
            ("notify_staff", "=", True),
        ], limit=1)
        if not rule:
            return []

        site_url = self._site_url()
        text = self._generic_message(record, message, company)
        pending = {}

        def add(partner, role):
            if rule.customer_locked and role == "customer":
                return
            if role == "customer" and not rule.notify_customer:
                return
            if role == "staff" and not rule.notify_staff:
                return
            if not partner or partner == message.author_id:
                return
            phone = self._phone(partner)
            if not phone:
                return
            event, use_template = self._event_for(record, subtype, role)
            item = {
                "role": role,
                "api_url": api_url,
                "api_key": api_key,
                "to": phone,
                "message": text,
                "event": event,
                "use_template": use_template,
                "site_url": site_url,
                "site_name": company.name or "",
                "variables": self._sale_variables(record, company, site_url) if use_template else {},
            }
            current = pending.get(phone)
            if not current or (role == "customer" and current["role"] != "customer"):
                pending[phone] = item

        if rule.notify_customer:
            for partner in record._wanoti_customer_partners():
                add(partner, "customer")
        if rule.notify_staff:
            for partner in record._wanoti_staff_partners(message):
                add(partner, "staff")

        payloads = []
        for phone, item in pending.items():
            key = (message.id, phone)
            if key in seen:
                continue
            seen.add(key)
            item.pop("role", None)
            payloads.append(item)
        return payloads

    @api.model
    def _deliver(self, payloads):
        import requests

        for payload in payloads:
            url = payload["api_url"].rstrip("/") + "/send/odoo"
            body = {
                "to": payload["to"],
                "message": payload["message"],
                "site_url": payload.get("site_url") or "",
                "site_name": payload.get("site_name") or "",
                "event": payload.get("event") or "",
                "use_template": bool(payload.get("use_template")),
            }
            body.update(payload.get("variables") or {})
            try:
                response = requests.post(
                    url,
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Api-Key": payload["api_key"],
                    },
                    timeout=20,
                )
            except Exception:
                _logger.exception("WaNoti request failed")
                continue
            if response.status_code >= 400:
                _logger.warning("WaNoti HTTP %s: %s", response.status_code, (response.text or "")[:300])

    @api.model
    def _test_connection(self, company):
        import requests

        api_url = (company.wanoti_api_url or "").strip().rstrip("/")
        api_key = (company.wanoti_api_key or "").strip()
        if not api_url or not api_key:
            return {"ok": False, "message": _("Add the API URL and API key first.")}
        if not company.wanoti_data_consent:
            return {
                "ok": False,
                "message": _("Turn on data sharing on this page before testing the connection."),
            }

        try:
            response = requests.post(
                api_url + "/plugin/ping",
                json={
                    "site_url": self._site_url(),
                    "plugin_version": "odoo-18.0.1.0.5",
                    "wp_version": "odoo-%s" % release.version,
                    "woocommerce_active": False,
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Api-Key": api_key,
                },
                timeout=20,
            )
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

        data = {}
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                data = response.json() or {}
            except Exception:
                data = {}
        if response.status_code >= 400 or data.get("success") is False:
            return {
                "ok": False,
                "message": data.get("message") or data.get("error") or (response.text or "")[:200],
            }
        if data.get("session_connected"):
            phone = data.get("session_phone") or ""
            return {"ok": True, "message": _("Connected. WhatsApp %s is online.") % phone}
        return {
            "ok": True,
            "message": _(
                "API key accepted. Connect WhatsApp in the WaNoti dashboard before notifications can send."
            ),
        }

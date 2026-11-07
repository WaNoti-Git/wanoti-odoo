from odoo import _, api, fields, models

from .wanoti_rule import EVENTS, MODULES


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wanoti_api_url = fields.Char(
        string="API URL",
        related="company_id.wanoti_api_url",
        readonly=False,
    )
    wanoti_api_key = fields.Char(
        string="API key",
        related="company_id.wanoti_api_key",
        readonly=False,
    )
    wanoti_data_consent = fields.Boolean(
        string="Allow data sharing",
        related="company_id.wanoti_data_consent",
        readonly=False,
    )
    wanoti_otp_login = fields.Boolean(
        string="Portal login code",
        related="company_id.wanoti_otp_login",
        readonly=False,
    )
    wanoti_otp_internal = fields.Boolean(
        string="Internal login code",
        related="company_id.wanoti_otp_internal",
        readonly=False,
    )
    wanoti_otp_passwordless = fields.Boolean(
        string="Code instead of password",
        related="company_id.wanoti_otp_passwordless",
        readonly=False,
    )
    wanoti_otp_checkout = fields.Boolean(
        string="Checkout code",
        related="company_id.wanoti_otp_checkout",
        readonly=False,
    )
    wanoti_otp_test_phone = fields.Char(string="Test mobile")
    wanoti_status_message = fields.Char(
        string="Connection status",
        compute="_compute_wanoti_status_message",
    )

    @api.depends_context("company")
    def _compute_wanoti_status_message(self):
        message = self.env["ir.config_parameter"].sudo().get_param("wanoti.status_message") or ""
        for record in self:
            record.wanoti_status_message = message

    @api.depends_context("company")
    def _compute_wanoti_events(self):
        rules = self.env["wanoti.rule"].sudo()
        rules._refresh_events()
        flags = {}
        company = self.env.company
        for rule in rules.search([("company_id", "=", company.id)]):
            xmlid = rule.subtype_id.get_external_id().get(rule.subtype_id.id)
            flags[xmlid] = (bool(rule.notify_customer), bool(rule.notify_staff))
        installed = rules._installed_modules()
        for record in self:
            for event in EVENTS:
                customer, staff = flags.get(event.xmlid, (False, False))
                record["wanoti_evt_%s_customer" % event.key] = customer
                record["wanoti_evt_%s_staff" % event.key] = staff
            for module in MODULES:
                record["wanoti_has_%s" % module] = module in installed

    def get_values(self):
        self.env["wanoti.rule"].sudo()._refresh_events()
        return super().get_values()

    def execute(self):
        self.ensure_one()
        action = self.env.context.get("wanoti_action")
        if action == "test":
            return self.action_wanoti_test()
        if action == "otp":
            return self.action_wanoti_test_otp()
        return super().execute()

    def _wanoti_notice(self, message, ok):
        self.env["ir.config_parameter"].sudo().set_param("wanoti.status_message", message or "")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WaNoti"),
                "message": message,
                "type": "success" if ok else "danger",
                "sticky": True,
            },
        }

    def action_wanoti_test(self):
        self.ensure_one()
        result = self.env["wanoti.dispatcher"]._test_connection(self.company_id)
        return self._wanoti_notice(result["message"], result["ok"])

    def action_open_rules(self):
        return self.env["wanoti.rule"].action_open_rules()

    def action_wanoti_test_otp(self):
        self.ensure_one()
        result = self.env["wanoti.otp"].sudo().create_challenge(
            self.company_id,
            self.wanoti_otp_test_phone,
            "test",
        )
        ok = bool(result.get("ok"))
        message = _("Code sent on WhatsApp.") if ok else result.get("message")
        return self._wanoti_notice(message, ok)

    for _event in EVENTS:
        for _role in ("customer", "staff"):
            _fname = "wanoti_evt_%s_%s" % (_event.key, _role)
            _xmlid = _event.xmlid

            def _inverse(self, xmlid=_xmlid, role=_role, fname=_fname):
                for record in self:
                    record.env["wanoti.rule"]._set_flag(
                        record.company_id, xmlid, role, record[fname]
                    )

            locals()[_fname] = fields.Boolean(
                string="Customer" if _role == "customer" else "Staff",
                compute="_compute_wanoti_events",
                inverse=_inverse,
            )
        del _role, _fname, _xmlid, _inverse
    del _event

    for _module in MODULES:
        locals()["wanoti_has_%s" % _module] = fields.Boolean(compute="_compute_wanoti_events")
    del _module

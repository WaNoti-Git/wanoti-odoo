from odoo import _, api, fields, models


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

from odoo import _, fields, models


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

    def action_wanoti_test(self):
        self.ensure_one()
        result = self.env["wanoti.dispatcher"]._test_connection(self.company_id)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WaNoti"),
                "message": result["message"],
                "type": "success" if result["ok"] else "danger",
                "sticky": not result["ok"],
            },
        }

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
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WaNoti"),
                "message": _("Code sent on WhatsApp.") if ok else result.get("message"),
                "type": "success" if ok else "danger",
                "sticky": not ok,
            },
        }

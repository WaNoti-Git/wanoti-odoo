from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    wanoti_api_url = fields.Char(
        string="WaNoti API URL",
        default="https://wanoti.net/api",
    )
    wanoti_api_key = fields.Char(string="WaNoti API key")
    wanoti_data_consent = fields.Boolean(
        string="Allow WaNoti data sharing",
        help="Phone numbers and the notification or code you enable are sent to WaNoti for WhatsApp delivery. Records stay in this database.",
    )
    wanoti_otp_login = fields.Boolean(
        string="Portal login OTP",
        help="Portal customers enter a WhatsApp code after their password.",
    )
    wanoti_otp_internal = fields.Boolean(
        string="Internal login OTP",
        help="Internal users enter a WhatsApp code after their password.",
    )
    wanoti_otp_passwordless = fields.Boolean(
        string="WhatsApp code login",
        help="Users with a mobile number can sign in with a new WhatsApp code instead of their password.",
    )
    wanoti_test_phone = fields.Char(string="WaNoti test mobile")
    wanoti_status_message = fields.Char(string="WaNoti status")
    wanoti_otp_checkout = fields.Boolean(
        string="Checkout OTP",
        help="Website customers confirm their phone on WhatsApp before payment.",
    )

from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _wanoti_otp_required(self):
        """Ask for a WhatsApp code when the owner enabled it for this kind of user."""
        self.ensure_one()
        if not self.active or self._is_public():
            return False
        company = self.company_id or self.env.company
        enabled = company.wanoti_otp_login if self.share else company.wanoti_otp_internal
        if not enabled:
            return False
        from .phone_utils import partner_raw_phone

        return bool(self.env["wanoti.otp"]._digits(partner_raw_phone(self.partner_id)))

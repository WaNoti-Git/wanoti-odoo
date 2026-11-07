from odoo import api, models

from .phone_utils import apply_phone_widget, partner_raw_phone


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
        return bool(self.env["wanoti.otp"]._digits(partner_raw_phone(self.partner_id)))

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "form":
            apply_phone_widget(arch)
        return arch, view

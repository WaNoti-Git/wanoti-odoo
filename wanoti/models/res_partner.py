from odoo import api, models

from .phone_utils import apply_phone_widget


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "form":
            apply_phone_widget(arch)
        return arch, view

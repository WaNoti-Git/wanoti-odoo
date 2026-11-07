def migrate(cr, version):
    """Keep databases that already connected from going silent."""
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].search([("wanoti_api_key", "!=", False)])
    for company in companies:
        if (company.wanoti_api_key or "").strip() and not company.wanoti_data_consent:
            company.wanoti_data_consent = True

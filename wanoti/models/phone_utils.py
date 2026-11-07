def partner_raw_phone(partner):
    """Prefer mobile. Odoo 19 contacts only have phone."""
    if not partner:
        return ""
    for name in ("mobile", "phone"):
        if name in partner._fields and partner[name]:
            return partner[name]
    return ""

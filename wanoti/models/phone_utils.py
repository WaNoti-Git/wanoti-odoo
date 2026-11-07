PHONE_FIELD_NAMES = {
    "phone",
    "mobile",
    "mobile_phone",
    "work_phone",
    "private_phone",
    "emergency_phone",
    "wanoti_otp_test_phone",
}


def apply_phone_widget(arch):
    """Use the country-code widget on phone fields in this form."""
    for node in arch.xpath(".//field"):
        if node.get("name") not in PHONE_FIELD_NAMES or _inside_subview(node):
            continue
        node.set("widget", "wanoti_phone")
    return arch


def _inside_subview(node):
    parent = node.getparent()
    while parent is not None:
        if parent.tag in ("kanban", "tree", "list", "search", "calendar", "activity"):
            return True
        parent = parent.getparent()
    return False


def partner_raw_phone(partner):
    """Prefer mobile. Odoo 19 contacts only have phone."""
    if not partner:
        return ""
    for name in ("mobile", "phone"):
        if name in partner._fields and partner[name]:
            return partner[name]
    return ""

import logging

_logger = logging.getLogger(__name__)


def _checkout_gate():
    from odoo.http import request

    website = getattr(request, "website", None)
    if not website or not hasattr(website, "sale_get_order"):
        return None
    order = website.sale_get_order()
    if not order:
        return None
    company = order.company_id or request.env.company
    if not company.wanoti_otp_checkout:
        return None
    phone = request.env["wanoti.otp"]._digits(order.partner_id.mobile or order.partner_id.phone or "")
    if (
        request.session.get("wanoti_checkout_ok") == order.id
        and request.session.get("wanoti_checkout_phone") == phone
        and phone
    ):
        return None
    return request.redirect("/shop/wanoti-otp")


def patch_website_sale():
    try:
        from odoo.addons.website_sale.controllers.main import WebsiteSale
    except Exception:
        _logger.info("WaNoti checkout OTP waits until Website Sales is installed.")
        return

    for name in ("shop_confirm_order", "shop_payment", "shop_payment_validate"):
        original = getattr(WebsiteSale, name, None)
        if not original or getattr(original, "_wanoti_wrapped", False):
            continue

        def wrapper(self, *args, _orig=original, **kwargs):
            gate = _checkout_gate()
            if gate is not None:
                return gate
            return _orig(self, *args, **kwargs)

        wrapper._wanoti_wrapped = True
        setattr(WebsiteSale, name, wrapper)

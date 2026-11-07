from urllib.parse import quote

from odoo import _, http
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.addons.web.controllers.home import Home


class WanotiHome(Home):
    def _password_ok(self, user, password):
        try:
            user.with_user(user)._check_credentials(password, {"interactive": False})
            return True
        except AccessDenied:
            return False
        except TypeError:
            try:
                user.with_user(user)._check_credentials(
                    {"type": "password", "password": password, "login": user.login},
                    {"interactive": False},
                )
                return True
            except AccessDenied:
                return False
            except TypeError:
                return None

    def _finish_login(self, user, redirect):
        user = user.sudo()
        request.session.pre_uid = user.id
        request.session.pre_login = user.login
        if hasattr(request.session, "finalize"):
            request.session.finalize(request.env)
        if not request.session.uid:
            request.session.uid = user.id
            request.session.login = user.login
            request.session.session_token = user._compute_session_token(request.session.sid)
            request.update_env(user=user.id)
        request.session.pop("wanoti_login_token", None)
        fallback = "/my" if user.share else "/web"
        target = redirect if redirect and redirect.startswith("/") and not redirect.startswith("//") else fallback
        return request.redirect(target)

    @http.route()
    def web_login(self, redirect=None, **kw):
        if request.httprequest.method == "POST":
            login = (request.params.get("login") or "").strip()
            password = request.params.get("password") or ""
            if login and password:
                user = request.env["res.users"].sudo().search([("login", "=", login)], limit=1)
                if user and user._wanoti_otp_required():
                    checked = self._password_ok(user, password)
                    if checked is None:
                        return request.render("wanoti.wanoti_otp_login", {
                            "error": _("WhatsApp verification could not check the password."),
                            "redirect": redirect or "",
                            "message": "",
                        })
                    if not checked:
                        return super().web_login(redirect=redirect, **kw)
                    phone = user.partner_id.mobile or user.partner_id.phone
                    result = request.env["wanoti.otp"].sudo().create_challenge(
                        user.company_id or request.env.company,
                        phone,
                        "login",
                        user=user,
                    )
                    if not result.get("ok"):
                        if result.get("offline"):
                            return self._finish_login(user, redirect)
                        return request.render("wanoti.wanoti_otp_login", {
                            "error": result.get("message"),
                            "redirect": redirect or "",
                            "message": "",
                        })
                    request.session["wanoti_login_token"] = result["token"]
                    safe = quote(redirect or "", safe="/")
                    return request.redirect("/web/login/wanoti-otp?redirect=%s" % safe)
        return super().web_login(redirect=redirect, **kw)

    @http.route("/web/login/wanoti-code", type="http", auth="public", methods=["POST"], sitemap=False)
    def wanoti_login_code(self, login=None, redirect=None, **kw):
        login = (login or "").strip()
        user = request.env["res.users"].sudo().search([("login", "=", login)], limit=1) if login else request.env["res.users"]
        company = user.company_id if user else request.env.company
        phone = user.partner_id.mobile or user.partner_id.phone if user else ""
        allowed = bool(
            user
            and user.active
            and not user._is_public()
            and company.wanoti_otp_passwordless
            and request.env["wanoti.otp"]._digits(phone)
        )
        if not allowed:
            return request.render("wanoti.wanoti_otp_login", {
                "error": _("We could not send a code for this login. Check it, and make sure the user has a mobile number."),
                "redirect": redirect or "",
                "message": "",
            })
        result = request.env["wanoti.otp"].sudo().create_challenge(company, phone, "login", user=user)
        if not result.get("ok"):
            message = result.get("message")
            if result.get("offline"):
                message = _("WhatsApp is disconnected, so a code cannot be sent. Sign in with your password.")
            return request.render("wanoti.wanoti_otp_login", {
                "error": message,
                "redirect": redirect or "",
                "message": "",
            })
        request.session["wanoti_login_token"] = result["token"]
        return request.redirect("/web/login/wanoti-otp?redirect=%s" % quote(redirect or "", safe="/"))

    @http.route("/web/login/wanoti-otp", type="http", auth="public", methods=["GET", "POST"], sitemap=False)
    def wanoti_login_otp(self, redirect=None, code=None, **kw):
        token = request.session.get("wanoti_login_token")
        challenge = request.env["wanoti.otp"].sudo().search([
            ("token", "=", token),
            ("purpose", "=", "login"),
        ], limit=1) if token else request.env["wanoti.otp"]
        if not challenge or challenge._expired():
            request.session.pop("wanoti_login_token", None)
            return request.redirect("/web/login")
        error = None
        if request.httprequest.method == "POST" and code is not None:
            result = challenge.verify(code)
            if result.get("ok"):
                return self._finish_login(challenge.user_id, redirect)
            error = result.get("message")
        return request.render("wanoti.wanoti_otp_login", {
            "error": error,
            "redirect": redirect or "",
            "message": "",
        })

    @http.route("/web/login/wanoti-otp/resend", type="http", auth="public", methods=["POST"], sitemap=False)
    def wanoti_login_otp_resend(self, redirect=None, **kw):
        token = request.session.get("wanoti_login_token")
        challenge = request.env["wanoti.otp"].sudo().search([
            ("token", "=", token),
            ("purpose", "=", "login"),
        ], limit=1) if token else request.env["wanoti.otp"]
        if not challenge:
            return request.redirect("/web/login")
        result = challenge.resend()
        if result.get("ok"):
            request.session["wanoti_login_token"] = result["token"]
            error = None
        else:
            error = result.get("message")
        return request.render("wanoti.wanoti_otp_login", {
            "error": error,
            "redirect": redirect or "",
            "message": _("A new code was sent.") if result.get("ok") else "",
        })


class WanotiCheckoutOtp(http.Controller):
    @http.route("/shop/wanoti-otp", type="http", auth="public", methods=["GET", "POST"], sitemap=False)
    def shop_otp(self, code=None, **kw):
        order = self._order()
        if not order:
            return request.redirect("/shop")
        company = order.company_id or request.env.company
        if not company.wanoti_otp_checkout:
            return request.redirect("/shop/checkout")
        phone = self._order_phone(order)
        error = None
        sent = bool(request.session.get("wanoti_checkout_token"))
        if request.httprequest.method == "POST":
            action = request.params.get("wanoti_action")
            if action == "send" or not sent:
                if not phone:
                    error = _("Add a mobile number on the customer before continuing.")
                else:
                    result = request.env["wanoti.otp"].sudo().create_challenge(
                        company, phone, "checkout", sale_order_id=order.id,
                    )
                    if result.get("ok"):
                        request.session["wanoti_checkout_token"] = result["token"]
                        request.session["wanoti_checkout_order"] = order.id
                        sent = True
                    elif result.get("offline"):
                        request.session["wanoti_checkout_ok"] = order.id
                        request.session["wanoti_checkout_phone"] = phone
                        return request.redirect("/shop/payment")
                    else:
                        error = result.get("message")
            elif action == "verify":
                token = request.session.get("wanoti_checkout_token")
                challenge = request.env["wanoti.otp"].sudo().search([
                    ("token", "=", token),
                    ("purpose", "=", "checkout"),
                    ("sale_order_id", "=", order.id),
                ], limit=1) if token else request.env["wanoti.otp"]
                if not challenge:
                    error = _("Send a new code.")
                    sent = False
                else:
                    result = challenge.verify(code or "")
                    if result.get("ok"):
                        request.session["wanoti_checkout_ok"] = order.id
                        request.session["wanoti_checkout_phone"] = phone
                        return request.redirect("/shop/payment")
                    error = result.get("message")
        return request.render("wanoti.wanoti_otp_checkout", {
            "error": error,
            "phone": phone,
            "sent": sent,
        })

    def _order(self):
        website = getattr(request, "website", None)
        if not website or not hasattr(website, "sale_get_order"):
            return None
        return website.sale_get_order()

    def _order_phone(self, order):
        partner = order.partner_id
        raw = partner.mobile or partner.phone or ""
        return request.env["wanoti.otp"]._digits(raw)

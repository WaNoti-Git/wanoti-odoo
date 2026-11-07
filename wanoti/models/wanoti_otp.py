from datetime import timedelta

from odoo import _, api, fields, models


class WanotiDispatcher(models.AbstractModel):
    _inherit = "wanoti.dispatcher"

    @api.model
    def _api_post(self, company, path, body=None):
        import requests

        api_url = (company.wanoti_api_url or "").strip().rstrip("/")
        api_key = (company.wanoti_api_key or "").strip()
        if not api_url or not api_key:
            return {"ok": False, "message": _("Add the API URL and API key first.")}
        if not company.wanoti_data_consent:
            return {
                "ok": False,
                "message": _("Turn on data sharing in WaNoti settings before a code can be sent."),
            }

        payload = {"site_url": self._site_url(), "site_name": company.name or ""}
        payload.update(body or {})
        try:
            response = requests.post(
                api_url + "/" + path.lstrip("/"),
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Api-Key": api_key,
                },
                timeout=20,
            )
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

        data = {}
        if "json" in (response.headers.get("content-type") or ""):
            try:
                data = response.json() or {}
            except Exception:
                data = {}
        if response.status_code >= 400 or data.get("success") is False:
            return {
                "ok": False,
                "message": data.get("message") or data.get("error") or (response.text or "")[:200],
                "data": data,
            }
        return {"ok": True, "data": data, "message": ""}

    @api.model
    def send_otp(self, company, phone, purpose="login"):
        return self._api_post(company, "/send/otp", {
            "to": phone,
            "purpose": purpose,
            "expiry_minutes": 10,
        })

    @api.model
    def verify_otp(self, company, otp_id, code):
        return self._api_post(company, "/verify/otp", {
            "otp_id": otp_id,
            "code": code,
        })


class WanotiOtp(models.Model):
    _name = "wanoti.otp"
    _description = "WaNoti WhatsApp code"
    _order = "id desc"

    company_id = fields.Many2one("res.company", required=True, index=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", ondelete="cascade", index=True)
    phone = fields.Char(required=True, index=True)
    purpose = fields.Char(required=True, index=True)
    otp_id = fields.Char()
    token = fields.Char(index=True)
    sale_order_id = fields.Integer(index=True)
    verified = fields.Boolean()
    expires_at = fields.Datetime()

    @api.model
    def _digits(self, raw):
        digits = "".join(ch for ch in (raw or "") if ch.isdigit())
        return digits if len(digits) >= 8 else ""

    def _expired(self):
        self.ensure_one()
        return bool(self.expires_at and self.expires_at < fields.Datetime.now())

    @api.model
    def _prune(self):
        limit = fields.Datetime.now() - timedelta(days=1)
        self.sudo().search([("create_date", "<", limit)]).unlink()

    @api.model
    def _rate_limited(self, phone):
        since = fields.Datetime.now() - timedelta(minutes=10)
        count = self.sudo().search_count([
            ("phone", "=", phone),
            ("create_date", ">=", since),
        ])
        return count >= 3

    @api.model
    def create_challenge(self, company, phone, purpose, user=None, sale_order_id=None):
        self._prune()
        digits = self._digits(phone)
        if not digits:
            return {"ok": False, "message": _("Enter a mobile number with the country code.")}
        if self._rate_limited(digits):
            return {"ok": False, "message": _("Too many codes were sent. Wait 10 minutes and try again.")}

        result = self.env["wanoti.dispatcher"].send_otp(company, digits, purpose)
        if not result.get("ok"):
            offline = (result.get("data") or {}).get("error") == "no_session"
            return {
                "ok": False,
                "offline": offline,
                "message": (
                    _("WhatsApp is disconnected, so the code could not be sent.")
                    if offline
                    else result.get("message") or _("Could not send the WhatsApp code.")
                ),
            }

        data = result.get("data") or {}
        token = __import__("secrets").token_urlsafe(24)
        expires = fields.Datetime.now() + timedelta(minutes=10)
        record = self.sudo().create({
            "company_id": company.id,
            "user_id": user.id if user else False,
            "phone": digits,
            "purpose": purpose,
            "otp_id": data.get("otp_id"),
            "token": token,
            "sale_order_id": sale_order_id or 0,
            "expires_at": expires,
        })
        return {"ok": True, "token": token, "id": record.id}

    def verify(self, code):
        self.ensure_one()
        code = "".join(ch for ch in (code or "") if ch.isdigit())
        if self.verified:
            return {"ok": True}
        if self._expired():
            return {"ok": False, "message": _("That code has expired. Send a new one.")}
        if len(code) != 6:
            return {"ok": False, "message": _("Enter the 6-digit code from WhatsApp.")}
        result = self.env["wanoti.dispatcher"].verify_otp(self.company_id, self.otp_id, code)
        if not result.get("ok") or not (result.get("data") or {}).get("verified"):
            return {"ok": False, "message": result.get("message") or _("That code is not valid.")}
        self.sudo().write({"verified": True})
        return {"ok": True}

    def resend(self):
        self.ensure_one()
        return self.env["wanoti.otp"].create_challenge(
            self.company_id,
            self.phone,
            self.purpose,
            user=self.user_id,
            sale_order_id=self.sale_order_id,
        )

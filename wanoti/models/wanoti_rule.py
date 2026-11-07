from odoo import _, api, fields, models

SKIP_PREFIXES = ("ir.", "bus.", "mail.", "wanoti.", "base_import.")


class WanotiRule(models.Model):
    _name = "wanoti.rule"
    _description = "WaNoti notification event"
    _order = "app_label, document, sequence, id"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        ondelete="cascade",
        default=lambda self: self.env.company,
    )
    model_id = fields.Many2one("ir.model", required=True, index=True, ondelete="cascade")
    subtype_id = fields.Many2one(
        "mail.message.subtype",
        string="Event",
        required=True,
        index=True,
        ondelete="cascade",
    )
    app_label = fields.Char(string="App", index=True)
    document = fields.Char(string="Document")
    sequence = fields.Integer(default=10)
    customer_locked = fields.Boolean(
        string="Customer locked",
        help="Private notes stay on the staff channel.",
    )
    notify_customer = fields.Boolean(string="Customer")
    notify_staff = fields.Boolean(string="Staff")

    _sql_constraints = [
        (
            "wanoti_rule_unique",
            "unique(company_id, model_id, subtype_id)",
            "This event is already listed.",
        ),
    ]

    @api.model
    def _thread_models(self):
        models = self.env["ir.model"].sudo().search(
            [("transient", "=", False), ("is_mail_thread", "=", True)]
        )
        return models.filtered(
            lambda model: model.model in self.env
            and not model.model.startswith(SKIP_PREFIXES)
        )

    @api.model
    def _app_label(self, model):
        module_name = (model.modules or "").split(",")[0].strip()
        if not module_name:
            return model.name or model.model
        module = self.env["ir.module.module"].sudo().search(
            [("name", "=", module_name)], limit=1
        )
        return module.shortdesc or module_name

    @api.model
    def _is_private_note(self, subtype):
        note = self.env.ref("mail.mt_note", raise_if_not_found=False)
        if not note or not subtype:
            return False
        return subtype == note or subtype.parent_id == note

    @api.model
    def _subtypes_for(self, model):
        subtype_model = self.env["mail.message.subtype"].sudo()
        generic = subtype_model.search(
            [("res_model", "=", False), ("hidden", "=", False), ("parent_id", "=", False)]
        )
        specific = subtype_model.search(
            [("res_model", "=", model.model), ("hidden", "=", False)]
        )
        return generic | specific

    @api.model
    def _refresh_events(self):
        """Add events for installed apps. Existing checkboxes are left as the owner set them."""
        companies = self.env["res.company"].sudo().search([])
        existing = {
            (rule.company_id.id, rule.model_id.id, rule.subtype_id.id): rule
            for rule in self.sudo().search([])
        }
        thread_models = self._thread_models()
        seen = set()
        to_create = []

        for company in companies:
            for model in thread_models:
                app_label = self._app_label(model)
                for subtype in self._subtypes_for(model):
                    key = (company.id, model.id, subtype.id)
                    seen.add(key)
                    locked = self._is_private_note(subtype)
                    current = existing.get(key)
                    if current:
                        vals = {}
                        if current.app_label != app_label:
                            vals["app_label"] = app_label
                        if current.document != model.name:
                            vals["document"] = model.name
                        if current.sequence != (subtype.sequence or 10):
                            vals["sequence"] = subtype.sequence or 10
                        if current.customer_locked != locked:
                            vals["customer_locked"] = locked
                        if locked and current.notify_customer:
                            vals["notify_customer"] = False
                        if vals:
                            current.write(vals)
                        continue
                    to_create.append({
                        "company_id": company.id,
                        "model_id": model.id,
                        "subtype_id": subtype.id,
                        "app_label": app_label,
                        "document": model.name,
                        "sequence": subtype.sequence or 10,
                        "customer_locked": locked,
                        "notify_customer": False,
                        "notify_staff": False,
                    })

        if to_create:
            self.sudo().create(to_create)

        stale = self.sudo().search([]).filtered(
            lambda rule: (rule.company_id.id, rule.model_id.id, rule.subtype_id.id) not in seen
            or rule.model_id.model not in self.env
        )
        if stale:
            stale.unlink()

    @api.model
    def action_open_rules(self):
        self._refresh_events()
        return {
            "type": "ir.actions.act_window",
            "name": _("Notifications"),
            "res_model": "wanoti.rule",
            "view_mode": "list",
            "target": "current",
            "context": {"search_default_group_app": 1},
            "domain": [("company_id", "in", self.env.companies.ids)],
            "help": _(
                "<p>Every event is off. Check Customer, Staff, or both for the apps you use.</p>"
            ),
        }

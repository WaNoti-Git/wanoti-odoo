from collections import namedtuple

from odoo import _, api, fields, models

Event = namedtuple(
    "Event",
    "key xmlid module app document label audience help",
)

# Business events Odoo already posts, plus delivery and point of sale.
# audience: both, staff, or vendor (the vendor uses the customer switch).
EVENTS = (
    Event("sale_sent", "sale.mt_order_sent", "sale", "Sales", "Quotation", "Quotation sent", "both",
          "WhatsApp when a quotation is sent."),
    Event("sale_confirmed", "sale.mt_order_confirmed", "sale", "Sales", "Sales order", "Order confirmed", "both",
          "WhatsApp when a quotation is confirmed."),
    Event("invoice_validated", "account.mt_invoice_validated", "account", "Invoicing", "Invoice", "Validated", "both",
          "WhatsApp when an invoice or bill is confirmed."),
    Event("invoice_paid", "account.mt_invoice_paid", "account", "Invoicing", "Invoice", "Paid", "both",
          "WhatsApp when an invoice is paid."),
    Event("po_sent", "purchase.mt_rfq_sent", "purchase", "Purchase", "Purchase order", "Sent to vendor", "vendor",
          "WhatsApp when a request for quotation is sent."),
    Event("po_confirmed", "purchase.mt_rfq_confirmed", "purchase", "Purchase", "Purchase order", "Confirmed", "vendor",
          "WhatsApp when a purchase order is confirmed."),
    Event("po_done", "purchase.mt_rfq_done", "purchase", "Purchase", "Purchase order", "Locked", "vendor",
          "WhatsApp when a purchase order is locked."),
    Event("crm_created", "crm.mt_lead_create", "crm", "CRM", "Opportunity", "Created", "both",
          "WhatsApp when a lead or opportunity is created."),
    Event("crm_stage", "crm.mt_lead_stage", "crm", "CRM", "Opportunity", "Stage changed", "staff",
          "WhatsApp to the salesperson when the stage changes."),
    Event("crm_won", "crm.mt_lead_won", "crm", "CRM", "Opportunity", "Won", "both",
          "WhatsApp when an opportunity is won."),
    Event("crm_lost", "crm.mt_lead_lost", "crm", "CRM", "Opportunity", "Lost", "staff",
          "WhatsApp to the salesperson when an opportunity is lost."),
    Event("task_new", "project.mt_task_new", "project", "Project", "Task", "Created", "both",
          "WhatsApp when a task is created."),
    Event("task_stage", "project.mt_task_stage", "project", "Project", "Task", "Stage changed", "both",
          "WhatsApp when a task changes stage."),
    Event("task_done", "project.mt_task_done", "project", "Project", "Task", "Done", "both",
          "WhatsApp when a task is marked done."),
    Event("picking_done", "wanoti.mt_picking_done", "stock", "Inventory", "Transfer", "Validated", "both",
          "WhatsApp when a delivery, receipt, or internal transfer is validated."),
    Event("pos_paid", "wanoti.mt_pos_paid", "point_of_sale", "Point of Sale", "Order", "Paid", "both",
          "WhatsApp when a point of sale order is paid."),
    Event("applicant_new", "hr_recruitment.mt_applicant_new", "hr_recruitment", "Recruitment", "Applicant", "New applicant", "staff",
          "WhatsApp to the recruiter when someone applies."),
    Event("applicant_hired", "hr_recruitment.mt_applicant_hired", "hr_recruitment", "Recruitment", "Applicant", "Hired", "both",
          "WhatsApp when an applicant is hired."),
    Event("leave", "hr_holidays.mt_leave", "hr_holidays", "Time Off", "Time off", "Requested", "staff",
          "WhatsApp to the employee and the manager when time off is requested."),
    Event("maint_new", "maintenance.mt_req_created", "maintenance", "Maintenance", "Request", "Created", "staff",
          "WhatsApp when a maintenance request is created."),
    Event("maint_status", "maintenance.mt_req_status", "maintenance", "Maintenance", "Request", "Status changed", "staff",
          "WhatsApp when a maintenance request changes status."),
)

MODULES = tuple(dict.fromkeys(event.module for event in EVENTS))
EVENT_BY_XMLID = {event.xmlid: event for event in EVENTS}


class WanotiRule(models.Model):
    _name = "wanoti.rule"
    _description = "WaNoti notification event"
    _order = "sequence, id"

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
    customer_locked = fields.Boolean(string="Customer locked")
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
    def _installed_modules(self):
        return set(
            self.env["ir.module.module"].sudo().search([("state", "=", "installed")]).mapped("name")
        )

    @api.model
    def _active_events(self):
        installed = self._installed_modules()
        found = []
        for index, event in enumerate(EVENTS):
            if event.module not in installed:
                continue
            subtype = self.env.ref(event.xmlid, raise_if_not_found=False)
            if not subtype or not subtype.res_model or subtype.res_model not in self.env:
                continue
            model = self.env["ir.model"].sudo().search([("model", "=", subtype.res_model)], limit=1)
            if not model:
                continue
            found.append((index, event, subtype, model))
        return found

    @api.model
    def _refresh_events(self):
        """Keep one row per business event that this database can actually send."""
        if self.env.context.get("wanoti_refreshing"):
            return
        self = self.with_context(wanoti_refreshing=True)
        companies = self.env["res.company"].sudo().search([])
        active = self._active_events()
        existing = {
            (rule.company_id.id, rule.subtype_id.id): rule
            for rule in self.sudo().search([])
        }
        wanted = set()
        to_create = []
        for company in companies:
            for index, event, subtype, model in active:
                key = (company.id, subtype.id)
                wanted.add(key)
                locked = event.audience == "staff"
                vals = {
                    "model_id": model.id,
                    "app_label": event.app,
                    "document": event.document,
                    "sequence": index,
                    "customer_locked": locked,
                }
                current = existing.get(key)
                if current:
                    if locked and current.notify_customer:
                        vals["notify_customer"] = False
                    changed = {name: value for name, value in vals.items() if current[name] != value}
                    if changed:
                        current.write(changed)
                    continue
                to_create.append({
                    "company_id": company.id,
                    "subtype_id": subtype.id,
                    "notify_customer": False,
                    "notify_staff": False,
                    **vals,
                })
        if to_create:
            self.sudo().create(to_create)
        stale = self.sudo().search([]).filtered(
            lambda rule: (rule.company_id.id, rule.subtype_id.id) not in wanted
        )
        if stale:
            stale.unlink()

    @api.model
    def _set_flag(self, company, xmlid, role, value):
        event = EVENT_BY_XMLID.get(xmlid)
        if not event or not company:
            return
        if role == "customer" and event.audience == "staff":
            value = False
        self._refresh_events()
        subtype = self.env.ref(xmlid, raise_if_not_found=False)
        if not subtype:
            return
        rule = self.sudo().search([
            ("company_id", "=", company.id),
            ("subtype_id", "=", subtype.id),
        ], limit=1)
        if not rule:
            return
        field_name = "notify_customer" if role == "customer" else "notify_staff"
        if rule[field_name] != bool(value):
            rule.write({field_name: bool(value)})

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
                "<p>These are the business events this database can send. "
                "Every switch starts off. Turn on Customer, Staff, or both.</p>"
            ),
        }

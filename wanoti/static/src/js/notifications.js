/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class WanotiNotificationsAction extends Component {
    static template = "wanoti.NotificationsAction";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.company = useService("company");
        this.state = useState({
            groups: [],
            query: "",
            ready: false,
        });
        onWillStart(() => this.load());
    }

    async load() {
        const companyIds = this.company.activeCompanyIds || [this.company.currentCompany.id];
        const rules = await this.orm.searchRead(
            "wanoti.rule",
            [["company_id", "in", companyIds]],
            ["app_label", "document", "subtype_id", "notify_customer", "notify_staff", "customer_locked", "sequence"],
            { order: "app_label, document, sequence, id" }
        );
        const groups = [];
        for (const rule of rules) {
            const name = rule.app_label || "Other";
            let group = groups.find((item) => item.name === name);
            if (!group) {
                group = { name, rules: [] };
                groups.push(group);
            }
            group.rules.push(rule);
        }
        this.state.groups = groups;
        this.state.ready = true;
    }

    get visibleGroups() {
        const query = this.state.query.trim().toLowerCase();
        if (!query) {
            return this.state.groups;
        }
        return this.state.groups
            .map((group) => ({
                name: group.name,
                rules: group.rules.filter((rule) => {
                    const event = (rule.subtype_id && rule.subtype_id[1]) || "";
                    return `${group.name} ${rule.document || ""} ${event}`.toLowerCase().includes(query);
                }),
            }))
            .filter((group) => group.rules.length);
    }

    eventName(rule) {
        return (rule.subtype_id && rule.subtype_id[1]) || "";
    }

    async toggle(rule, field) {
        if (field === "notify_customer" && rule.customer_locked) {
            return;
        }
        const value = !rule[field];
        await this.orm.write("wanoti.rule", [rule.id], { [field]: value });
        rule[field] = value;
    }
}

registry.category("actions").add("wanoti_notifications", WanotiNotificationsAction);

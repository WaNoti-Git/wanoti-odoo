/** @odoo-module **/

import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { COUNTRIES, combinePhone, defaultIso, splitPhone } from "./country_codes";

export class WanotiPhoneField extends Component {
    static template = "wanoti.PhoneField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        "*": true,
    };

    setup() {
        const parts = splitPhone(this._raw(this.props));
        this.state = useState({
            iso: parts.matched ? parts.iso : defaultIso(),
            local: parts.local,
        });
        this.countries = COUNTRIES.slice().sort((a, b) => a.name.localeCompare(b.name));
        onWillUpdateProps((next) => this._sync(next));
    }

    _raw(props) {
        const value = props.record.data[props.name];
        return value ? String(value) : "";
    }

    _sync(props) {
        const digits = this._raw(props).replace(/\D/g, "");
        if (digits === combinePhone(this.state.iso, this.state.local)) {
            return;
        }
        const parts = splitPhone(digits);
        this.state.iso = parts.matched ? parts.iso : this.state.iso || defaultIso();
        this.state.local = parts.local;
    }

    get digits() {
        return this._raw(this.props).replace(/\D/g, "");
    }

    get display() {
        return this.digits ? `+${this.digits}` : "";
    }

    get countryLabel() {
        return _t("Country code");
    }

    get inputPlaceholder() {
        return this.props.placeholder || _t("Mobile number");
    }

    countryText(country) {
        return `${country.name}  +${country.dial}`;
    }

    commit() {
        const value = combinePhone(this.state.iso, this.state.local);
        const current = this._raw(this.props).replace(/\D/g, "");
        if (value !== current) {
            this.props.record.update({ [this.props.name]: value });
        }
    }

    onCountry(ev) {
        this.state.iso = ev.target.value;
        this.commit();
    }

    onLocal(ev) {
        let local = ev.target.value.replace(/\D/g, "").replace(/^0+/, "");
        const country = COUNTRIES.find((item) => item.code === this.state.iso);
        if (country && local.startsWith(country.dial) && local.length - country.dial.length >= 6) {
            local = local.slice(country.dial.length).replace(/^0+/, "");
        }
        this.state.local = local;
        this.commit();
    }
}

export const wanotiPhoneField = {
    component: WanotiPhoneField,
    displayName: _t("Phone"),
    supportedTypes: ["char"],
    extractProps({ attrs, placeholder }) {
        return {
            placeholder: placeholder || (attrs && attrs.placeholder) || "",
        };
    },
};

const fields = registry.category("fields");
const registerField = fields.add.bind(fields);
fields.add = function (key, value, options) {
    if (key === "phone" || key === "form.phone") {
        return registerField(key, wanotiPhoneField, { ...(options || {}), force: true });
    }
    return registerField(key, value, options);
};
registerField("wanoti_phone", wanotiPhoneField);
registerField("phone", wanotiPhoneField, { force: true });
registerField("form.phone", wanotiPhoneField, { force: true });

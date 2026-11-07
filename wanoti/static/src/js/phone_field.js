/** @odoo-module **/

import { Component, onWillUpdateProps, useExternalListener, useRef, useState } from "@odoo/owl";
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
            open: false,
            query: "",
            active: 0,
        });
        this.countries = COUNTRIES.slice().sort((a, b) => a.name.localeCompare(b.name));
        this.rootRef = useRef("root");
        this.searchRef = useRef("search");
        onWillUpdateProps((next) => this._sync(next));
        useExternalListener(window, "pointerdown", (ev) => this._closeIfOutside(ev));
        useExternalListener(window, "scroll", (ev) => this._closeOnScroll(ev), { capture: true });
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

    _closeIfOutside(ev) {
        const root = this.rootRef.el;
        if (this.state.open && root && !root.contains(ev.target)) {
            this.state.open = false;
        }
    }

    _closeOnScroll(ev) {
        const root = this.rootRef.el;
        if (!this.state.open || !root) {
            return;
        }
        if (ev && ev.target && (ev.target === root || root.contains(ev.target))) {
            return;
        }
        this.state.open = false;
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

    get searchPlaceholder() {
        return _t("Search country");
    }

    get emptyLabel() {
        return _t("No country found");
    }

    get inputPlaceholder() {
        return this.props.placeholder || _t("Mobile number");
    }

    get selectedCountry() {
        return this.countries.find((country) => country.code === this.state.iso);
    }

    get selectedText() {
        return this.selectedCountry ? this.countryText(this.selectedCountry) : this.countryLabel;
    }

    get visibleCountries() {
        const query = this.state.query.trim().toLowerCase().replace(/^\+/, "");
        if (!query) {
            return this.countries;
        }
        return this.countries.filter((country) => {
            return country.name.toLowerCase().includes(query)
                || country.code.toLowerCase() === query
                || country.dial.startsWith(query);
        });
    }

    get menuStyle() {
        const button = this.rootRef.el && this.rootRef.el.querySelector(".o_wanoti_phone_toggle");
        if (!button) {
            return "";
        }
        const box = button.getBoundingClientRect();
        const width = Math.max(box.width, 240);
        const left = Math.min(box.left, window.innerWidth - width - 8);
        return `top:${Math.round(box.bottom + 4)}px;left:${Math.round(Math.max(8, left))}px;width:${Math.round(width)}px;`;
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

    toggleCountry() {
        this.state.open = !this.state.open;
        this.state.query = "";
        if (!this.state.open) {
            return;
        }
        const index = this.visibleCountries.findIndex((country) => country.code === this.state.iso);
        this.state.active = index >= 0 ? index : 0;
        setTimeout(() => {
            const input = this.searchRef.el;
            if (input) {
                input.focus();
            }
            this.scrollActive();
        }, 0);
    }

    onSearch(ev) {
        this.state.query = ev.target.value;
        this.state.active = 0;
    }

    onSearchKey(ev) {
        const list = this.visibleCountries;
        if (ev.key === "ArrowDown") {
            ev.preventDefault();
            this.state.active = Math.min(this.state.active + 1, Math.max(list.length - 1, 0));
            this.scrollActive();
        } else if (ev.key === "ArrowUp") {
            ev.preventDefault();
            this.state.active = Math.max(this.state.active - 1, 0);
            this.scrollActive();
        } else if (ev.key === "Enter") {
            ev.preventDefault();
            const country = list[this.state.active];
            if (country) {
                this.pickCountry(country);
            }
        } else if (ev.key === "Escape") {
            ev.preventDefault();
            this.state.open = false;
        }
    }

    onPick(ev) {
        const code = ev.currentTarget.dataset.code;
        const country = this.countries.find((item) => item.code === code);
        if (country) {
            this.pickCountry(country);
        }
    }

    pickCountry(country) {
        this.state.iso = country.code;
        this.state.open = false;
        this.state.query = "";
        this.commit();
    }

    scrollActive() {
        const root = this.rootRef.el;
        if (!root) {
            return;
        }
        const option = root.querySelectorAll(".o_wanoti_phone_option")[this.state.active];
        if (option) {
            option.scrollIntoView({ block: "nearest" });
        }
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

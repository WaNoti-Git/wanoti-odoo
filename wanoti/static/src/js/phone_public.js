/** @odoo-module **/

import { combinePhone, defaultIso, splitPhone, COUNTRIES } from "./country_codes";

const NAMES = new Set(["phone", "mobile"]);

function countryOptions(selected) {
    return COUNTRIES.slice()
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((country) => {
            const option = document.createElement("option");
            option.value = country.code;
            option.textContent = `${country.name}  +${country.dial}`;
            option.selected = country.code === selected;
            return option;
        });
}

function formCountry(input) {
    const form = input.form;
    if (!form) {
        return "";
    }
    const select = form.querySelector("select[name='country_id']");
    const option = select && select.selectedOptions && select.selectedOptions[0];
    const code = option && (option.getAttribute("code") || option.dataset.code || "");
    return code && COUNTRIES.some((country) => country.code === code) ? code : "";
}

function enhance(input) {
    if (!input || input.dataset.wanotiPhone || input.closest(".o_wanoti_phone")) {
        return;
    }
    if (input.type === "hidden" || input.disabled) {
        return;
    }
    const name = input.getAttribute("name") || "";
    if (!NAMES.has(name)) {
        return;
    }
    input.dataset.wanotiPhone = "1";
    const parts = splitPhone(input.value);
    const iso = parts.matched ? parts.iso : formCountry(input) || defaultIso();
    const wrap = document.createElement("span");
    wrap.className = "o_wanoti_phone";
    const select = document.createElement("select");
    select.className = "form-control o_wanoti_phone_country";
    select.setAttribute("aria-label", "Country code");
    countryOptions(iso).forEach((option) => select.appendChild(option));
    const local = document.createElement("input");
    local.type = "tel";
    local.inputMode = "numeric";
    local.className = input.className || "form-control";
    local.placeholder = "Mobile number";
    local.autocomplete = "tel-national";
    local.value = parts.local;
    const sync = () => {
        const next = combinePhone(select.value, local.value);
        if (next) {
            input.value = next;
        }
    };
    select.addEventListener("change", () => {
        local.value = local.value.replace(/\D/g, "").replace(/^0+/, "");
        sync();
        input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    local.addEventListener("input", () => {
        let value = local.value.replace(/\D/g, "").replace(/^0+/, "");
        const country = COUNTRIES.find((item) => item.code === select.value);
        if (country && value.startsWith(country.dial) && value.length - country.dial.length >= 6) {
            value = value.slice(country.dial.length).replace(/^0+/, "");
        }
        local.value = value;
        sync();
        input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    input.type = "hidden";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(select);
    wrap.appendChild(local);
    wrap.appendChild(input);
    if (parts.matched) {
        sync();
    }
}

function scan(root) {
    const scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll("input[name='phone'], input[name='mobile']").forEach(enhance);
    if (root && root.matches && root.matches("input[name='phone'], input[name='mobile']")) {
        enhance(root);
    }
}

function start() {
    scan(document);
    const observer = new MutationObserver((records) => {
        records.forEach((record) => {
            record.addedNodes.forEach((node) => {
                if (node.nodeType === 1) {
                    scan(node);
                }
            });
        });
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
} else {
    start();
}

/** @odoo-module **/

import { combinePhone, defaultIso, splitPhone, COUNTRIES } from "./country_codes";

const NAMES = new Set(["phone", "mobile"]);
const COUNTRY_LIST = COUNTRIES.slice().sort((a, b) => a.name.localeCompare(b.name));

function countryLabel(country) {
    return `${country.name}  +${country.dial}`;
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

function buildPicker(iso, onChange) {
    const wrap = document.createElement("span");
    wrap.className = "o_wanoti_phone_country";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "form-control o_wanoti_phone_toggle";
    button.setAttribute("aria-label", "Country code");
    const label = document.createElement("span");
    label.className = "o_wanoti_phone_toggle_label";
    const caret = document.createElement("i");
    caret.className = "fa fa-caret-down";
    caret.setAttribute("aria-hidden", "true");
    button.appendChild(label);
    button.appendChild(caret);
    const menu = document.createElement("span");
    menu.className = "o_wanoti_phone_menu";
    menu.hidden = true;
    const search = document.createElement("input");
    search.type = "text";
    search.className = "form-control o_wanoti_phone_search";
    search.placeholder = "Search country";
    search.autocomplete = "off";
    search.setAttribute("aria-label", "Search country");
    const list = document.createElement("span");
    list.className = "o_wanoti_phone_options";
    let current = iso;
    const buttons = COUNTRY_LIST.map((country) => {
        const option = document.createElement("button");
        option.type = "button";
        option.className = "o_wanoti_phone_option";
        option.textContent = countryLabel(country);
        option.dataset.code = country.code;
        option.addEventListener("click", () => {
            current = country.code;
            label.textContent = countryLabel(country);
            menu.hidden = true;
            onChange(current);
        });
        list.appendChild(option);
        return { country, option };
    });
    const showLabel = () => {
        const country = COUNTRY_LIST.find((item) => item.code === current) || COUNTRY_LIST[0];
        label.textContent = country ? countryLabel(country) : "Country code";
    };
    const place = () => {
        const box = button.getBoundingClientRect();
        const width = Math.max(box.width, 240);
        const left = Math.min(box.left, window.innerWidth - width - 8);
        menu.style.top = `${Math.round(box.bottom + 4)}px`;
        menu.style.left = `${Math.round(Math.max(8, left))}px`;
        menu.style.width = `${Math.round(width)}px`;
    };
    showLabel();
    button.addEventListener("click", () => {
        const willOpen = menu.hidden;
        document.querySelectorAll(".o_wanoti_phone_menu").forEach((node) => {
            node.hidden = true;
        });
        if (!willOpen) {
            return;
        }
        search.value = "";
        buttons.forEach((item) => {
            item.option.hidden = false;
        });
        menu.hidden = false;
        place();
        search.focus();
    });
    search.addEventListener("input", () => {
        const query = search.value.trim().toLowerCase().replace(/^\+/, "");
        buttons.forEach((item) => {
            const hay = `${item.country.name} ${item.country.code}`.toLowerCase();
            item.option.hidden = Boolean(query) && !hay.includes(query) && !item.country.dial.startsWith(query);
        });
    });
    search.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === "Escape") {
            ev.preventDefault();
        }
        if (ev.key === "Escape") {
            menu.hidden = true;
        }
    });
    menu.appendChild(search);
    menu.appendChild(list);
    wrap.appendChild(button);
    wrap.appendChild(menu);
    return {
        wrap,
        get iso() {
            return current;
        },
    };
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
    const local = document.createElement("input");
    local.type = "tel";
    local.inputMode = "numeric";
    local.className = input.className || "form-control";
    local.placeholder = "Mobile number";
    local.autocomplete = "tel-national";
    local.value = parts.local;
    const sync = (countryIso) => {
        const next = combinePhone(countryIso, local.value);
        if (next) {
            input.value = next;
        }
    };
    const picker = buildPicker(iso, (countryIso) => {
        local.value = local.value.replace(/\D/g, "").replace(/^0+/, "");
        sync(countryIso);
        input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    local.addEventListener("input", () => {
        let value = local.value.replace(/\D/g, "").replace(/^0+/, "");
        const country = COUNTRIES.find((item) => item.code === picker.iso);
        if (country && value.startsWith(country.dial) && value.length - country.dial.length >= 6) {
            value = value.slice(country.dial.length).replace(/^0+/, "");
        }
        local.value = value;
        sync(picker.iso);
        input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    input.type = "hidden";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(picker.wrap);
    wrap.appendChild(local);
    wrap.appendChild(input);
    if (parts.matched) {
        sync(picker.iso);
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
    document.addEventListener("pointerdown", (ev) => {
        document.querySelectorAll(".o_wanoti_phone_menu").forEach((menu) => {
            if (!menu.hidden && menu.parentNode && !menu.parentNode.contains(ev.target)) {
                menu.hidden = true;
            }
        });
    });
    window.addEventListener("scroll", (ev) => {
        document.querySelectorAll(".o_wanoti_phone_menu").forEach((menu) => {
            if (!menu.hidden && menu.parentNode && ev.target !== menu.parentNode && !menu.parentNode.contains(ev.target)) {
                menu.hidden = true;
            }
        });
    }, true);
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

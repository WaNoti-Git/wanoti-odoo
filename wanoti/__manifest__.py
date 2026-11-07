{
    "name": "WhatsApp Notifications",
    "summary": "WhatsApp channel beside email and inbox",
    "description": """
WhatsApp notifications for the apps installed on this database.
Built for Odoo 18. The same module is published for Odoo 17 and 19.

This module needs the external WaNoti service. It installs and opens
without an activation key. Nothing is sent until an administrator
allows data sharing and turns an event on.

Phone numbers, the message text, and sale details for enabled events
are sent to WaNoti so they can be delivered on the company's own
WhatsApp number. Odoo keeps the records. The privacy policy is linked
from the data sharing setting inside the module.

Every event starts off. Customer, Staff, portal login, internal login,
a code instead of a password, and website checkout codes stay off
until the administrator enables them. If WhatsApp is disconnected,
password login and checkout continue.
    """,
    "version": "18.0.1.0.11",
    "category": "Productivity/Discuss",
    "author": "WaNoti",
    "website": "https://wanoti.net",
    "support": "support@wanoti.com",
    "license": "LGPL-3",
    "external_dependencies": {"python": ["requests"]},
    "images": ["static/description/banner.png"],
    "depends": ["mail", "web"],
    "data": [
        "data/wanoti_message_subtypes.xml",
        "security/ir.model.access.csv",
        "security/wanoti_security.xml",
        "views/wanoti_rule_views.xml",
        "views/res_config_settings_views.xml",
        "views/otp_templates.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wanoti/static/src/scss/notifications.scss",
            "wanoti/static/src/xml/notifications.xml",
            "wanoti/static/src/js/notifications.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
}

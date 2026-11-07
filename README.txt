WhatsApp Notifications for Odoo
===============================

One module, technical name wanoti, on three branches:

17.0  Odoo 17   version 17.0.1.0.5
18.0  Odoo 18   version 18.0.1.0.5
19.0  Odoo 19   version 19.0.1.0.5

Register this repository at https://apps.odoo.com while signed in
to the vendor account. Odoo reads these branch names. There is no
main branch on purpose, so the store does not publish a fourth copy.

The module is free. Sending uses a WaNoti account and an API key.

Where it can be installed
-------------------------
Odoo Online (a database on odoo.com) cannot install this module.
Odoo.sh: add the wanoti folder to the project repository and push.
Odoo.sh rebuilds, then Apps → Update Apps List → Activate.
Your own server: copy the wanoti folder into the addons path, restart
Odoo, then Apps → Update Apps List → Activate.

The zip for each version contains one wanoti folder. __manifest__.py
is directly inside that folder.

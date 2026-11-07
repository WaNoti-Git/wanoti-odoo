WaNoti for Odoo 19
===========================

WhatsApp becomes a notification channel next to Email and Inbox.
The event list is built from the apps installed on the database
(Project, Helpdesk, Inventory, Manufacturing, Accounting, CRM,
Employees, Sales, and any other app that posts notifications).
Every checkbox starts off. Nothing is sent until the owner turns
an event on.

Install
-------
1. Copy the wanoti folder into your Odoo addons path.
2. Restart Odoo and update the Apps list.
3. Install "WhatsApp Notifications".
4. Open wanoti.net and create an account.
5. In that account, open Dashboard, then Plugins, and copy the API key.
6. In Odoo, open WaNoti, then Settings.
7. Turn on data sharing. Phone numbers and enabled messages are then sent to WaNoti.
8. Keep the API URL as https://wanoti.net/api.
9. Paste the API key, then click Test connection.
10. Connect WhatsApp in the WaNoti dashboard if it is not already online.
11. Open WaNoti → Notifications.
12. Check Customer, Staff, or both on the events you want.
    Customer uses the mobile or phone on the document contact.
    Staff uses the mobile or phone on the assigned user.
    Private notes can be sent to staff only.

After you install another Odoo app, open Notifications again.
New events are added still turned off.

Sales quotations and confirmed orders use your WaNoti order templates.
Every other event sends the document name, the update, and a link.

WhatsApp codes
--------------
Portal login, internal user login, code-instead-of-password, and website checkout codes start off.

Portal login and internal user login are separate switches.
Once enabled, that user enters a 6-digit WhatsApp code after the
password. The user needs a mobile or phone on their contact.
A user with no number still signs in with the password only.

Code instead of password is a third switch. Once enabled, the
login page offers "Send a WhatsApp code instead". A user who has
a mobile number receives a new code and signs in with that code.

Website checkout, once enabled, asks for that code before payment
when the Website Sales app is installed.

Send a test code from WaNoti → Connection. Three codes can be sent
to the same number every 10 minutes.

If the WhatsApp session is disconnected, a code cannot be sent.
A user who already typed the correct password is signed in anyway.
Code-instead-of-password asks them to use their password.
Checkout continues to payment. Document notifications are saved
in Odoo and the failed send stays in the WaNoti message log until
the session is connected again.

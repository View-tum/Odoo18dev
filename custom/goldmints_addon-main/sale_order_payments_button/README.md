# Sale Order Payments Smart Button


This module adds a Payments smart button to the Sale Order form in Odoo 18.


## Installation
1. Copy folder `sale_order_payments_button` to your Odoo addons path.
2. Update apps list in Odoo (Apps -> Update Apps List) or restart Odoo server.
3. Install module "Sale Order Payments Smart Button".


## Notes
- Adjust `models/sale_order.py` if your database stores invoice->payment relation in different fields.
- If you get JS errors on the web client, check browser devtools console for stack trace.
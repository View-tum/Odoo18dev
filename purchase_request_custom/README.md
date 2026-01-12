# purchase_request_custom

Blocks creating a new RFQ from the Purchase Request wizard when the selected PR line's product is already fully covered by existing RFQs/POs.

## Install
- Copy this folder into your Odoo addons path.
- Update app list and install **Purchase Request Custom**.

## Notes
- Depends on `purchase_request` and `purchase`.
- If your flow uses different PO states to count coverage, adjust the lambda in the wizard file.
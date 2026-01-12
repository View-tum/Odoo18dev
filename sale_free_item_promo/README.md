# Sale: Free Item Promo (Auto Bundle)

Adds automatic free item lines to quotations/sales orders **only if the customer is marked as eligible** on the Customer Master.

## How it works
- On the **Customer** (Contacts) form, tick **Eligible for Free Item Promo**.
- On the **Product** form, enable **Free Item Promo** and set:
  - **Free Item** (product to add for free)
  - **Free Item Qty per Unit** (quantity of the free item for each purchased unit)
- When you create or edit a quotation/order:
  - If the customer is eligible, the module adds or updates zero-priced lines for the free items.
  - If the customer is not eligible, any existing free item lines on that order are removed.
- Free lines are marked with **Is Free Item** and the name prefix `[FREE]` so users can easily identify and manually remove them if needed.

## Notes
- Free lines use the free product's default UoM and taxes, with **price = 0.00**.
- Quantities automatically scale with purchased units of the triggering product.
- Users can remove free lines manually; they may be re-added on future edits if eligibility and product settings still apply.

## Compatibility
- Tested for Odoo 18.0 (depends: `sale_management`, `product`).
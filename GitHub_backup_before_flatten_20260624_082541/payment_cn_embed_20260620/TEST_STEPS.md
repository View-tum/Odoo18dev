# Payment CN Embedded / Register Payment Test Steps

## Scope
- Standard Register Payment must create one payment journal entry when selecting an invoice/bill together with same-side credit note.
- Payment Difference must be 0 when the selected invoice/bill net amount equals payment amount.
- Customer CN and Vendor CN lines must be embedded in the payment journal entry, not created as a separate settlement journal.
- Existing cheque/bank draft methods are preserved when their own payment method line is explicitly selected.

## Backend Tests
1. Update modules: account_partner_settlement, account_payment_default_journal, account_payment_multi_allocation.
2. Run: python server\odoo-bin -c server\odoo.conf -d GoldMints_Uat_Manu -u account_partner_settlement,account_payment_default_journal,account_payment_multi_allocation --test-enable --test-tags /account_partner_settlement,/account_payment_default_journal --stop-after-init --no-http
3. Expected: 0 failed, 0 errors.

## UI E2E Test
1. Open local Odoo at http://127.0.0.1:8811, db GoldMints_Uat_Manu, login admin/admin.
2. Use existing partner DENKI SHOJI CO.,LTD.; no new product/vendor/customer master data is required.
3. Create/post test documents:
   - Customer invoice 100 and customer credit note 25.
   - Vendor bill 100 and vendor credit note 25.
   - Normal customer invoice 80.
4. From Invoice/Bill list view, select the invoice and credit note together, click Pay/Register Payment.
5. Expected wizard result:
   - Amount is net amount 75 for invoice/bill plus CN.
   - No Payment Difference is shown.
   - Journal/method has a valid payment account.
6. Click Create Payment.
7. Expected backend result:
   - Invoice/bill and credit note residual = 0.
   - Payment state = paid.
   - One account.payment and one payment journal entry are created per scenario.
   - Payment journal entry contains AR/AP lines for both invoice and credit note.

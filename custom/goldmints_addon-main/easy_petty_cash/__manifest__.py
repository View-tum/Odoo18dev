{
    "name": "Easy Petty Cash",
    "version": "18.0.1.0.0",
    "summary": "สมุดคุมเงินสดย่อยที่ง่ายที่สุด รวม In/Out และ WHT ในหน้าเดียว",
    "description": """
Petty Cash Management for Odoo 18 Enterprise.
Simplified petty cash logbook with integrated Thai tax support (VAT/WHT) and seamless HR Expense payment workflow.
Features:
- Unified In/Out Logbook.
- One-click 'Pay with Petty Cash' for Expenses.
- Selection Wizard with real-time Balance Check.
- Thai Tax Invoice tracking.
    """,
    "author": "Wolapart",
    "website": "https://www.365infotech.com",
    "category": "Accounting/Accounting",
    "license": "LGPL-3",
    "depends": [
        "account",
        "mail",
        "hr_expense",
        "l10n_th_account_tax_expense",
        "analytic",
    ],
    "data": [
        "data/sequence.xml",
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "views/res_config_settings_views.xml",
        "views/petty_cash_view.xml",
        "views/hr_expense_view.xml",
        "views/account_journal_view.xml",
        "wizard/petty_cash_payment_wizard_view.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
}

{
    'name': 'Invoice Payment Report',
    'version': '18.0.1.0.1',
    'summary': 'Provides an "Invoice Payment Report" wizard, allowing users to generate a Jasper report filtered by partners and a date range.',
    'description': """
        This module adds a new wizard to generate an "Invoice Payment Report" based on Jasper.

        Key Features:
        * Adds a new menu item "Invoice Payment Report" under the Invoicing > Reporting > Accounting Reports menu.
        * Provides a wizard (Transient Model) to configure report parameters.
        * Requires the user to select one or more Partners.
        * Requires selection of a "Date From" and "Date To" range.
        * Automatically populates default dates and finds the correct Jasper report template when partners are selected.
        * Includes validation to ensure the "Date From" is not later than the "Date To".
        * Integrates with 'oi_jasper_report' to generate the final report, passing the selected partner IDs and date range as parameters.
    """,
    'author': 'Noppadon Panboonyeun',
    'website': 'https://www.365infotech.co.th/',
    "license": "LGPL-3",
    'depends': [
        'base',
        'account',
        'deposit_payment_report',
        'oi_jasper_report',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/invoice_payment_report_view.xml',
        'views/menu_view.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
}
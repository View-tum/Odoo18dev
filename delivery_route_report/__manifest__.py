{
    'name': 'Delivery Route Report',
    'version': '18.0.2.0.0',
    "summary": 'Adds a "Delivery Route Report" wizard, allowing users to generate a Jasper report filtered by routes and date range.',
    "description": """
        This module introduces a wizard for generating a "Delivery Route Report".

        Key Features:
        * Adds a new menu item "Delivery Route Report" under a parent menu (invetory_reports_menu).
        * Provides a wizard (Transient Model `delivery.route.report`) for users to configure report parameters.
        * Requires users to select one or more Delivery Routes.
        * Requires users to specify a "Date From" and "Date To" range.
        * Automatically sets default dates (first day of the current month to today) and finds the associated Jasper report template when routes are selected.
        * Includes validation to ensure the "Date From" is not later than the "Date To".
        * Integrates with 'oi_jasper_report' to generate the final report, passing the selected route IDs and date range as parameters.
    """,
    'author': '365 infotech',
    'website': 'https://www.365infotech.co.th/',
    "license": "LGPL-3",
    'depends': [
        'base',
        'delivery_routes_management',
        'delivery_pickup_transport',
        'oi_jasper_report',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/delivery_route_report_view.xml',
        'views/menu_view.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
}
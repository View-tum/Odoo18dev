# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
{
    "name": "All In One Cancel - Advance | All In One Cancel and Delete",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Extra Tools",
    "license": "OPL-1",
    "summary": "Cancel Sale Order Cancel Quotation Cancel Purchase Order Cancel Request For Quotation Cancel POS Order Cancel MRP Order Cancel Invoice Cancel Payment Cancel Stock Picking Cancel Stock Moves Odoo Cancel Inventory Cancel Landed Cost Cancel HR Expense Cancel HR Expance Cancel Multiple Records Cancel Individual Records Cancel Scrap Orders Cancel Manufacturing Orders Cancel SO Cancel Quote Cancel PO Cancel RFQ Cancel Point Of Sale Orders Cancel Bill Cancel Account Cancel Acc Delete Sale Order Delete Quotation Delete Purchase Order Delete Request For Quotation Delete POS Order Delete MRP Order Delete Invoice Delete Payment Delete Stock Picking Delete Stock Moves Odoo Delete Inventory Delete Landed Cost Delete HR Expense Delete HR Expance Delete Multiple Records Delete Individual Records Delete Scrap Orders Delete Manufacturing Orders Delete SO Delete Quote Delete PO Delete RFQ Delete Point Of Sale Orders Delete Bill Delete Account Delete Acc ",
    "description": """This module helps to cancel sale orders, purchase orders, invoices, payments, inventory (inventory transfer,stock move & scrap Orders), manufacturing orders, landed costs, HR Expenses, point of sale orders. You can also cancel multiple records from the tree view.""",
    "version": "0.0.5",
    "depends": [
              "account", "purchase", "sale_management", "stock", "hr_expense", "stock_landed_costs", "mrp",
    ],
    "application": True,
    "data": [
        # Account Cancel 
        'sh_account_cancel/security/account_groups.xml',
        'sh_account_cancel/data/server_action_data.xml',
        'sh_account_cancel/views/res_config_settings_views.xml',
        'sh_account_cancel/views/account_move_views.xml',
        'sh_account_cancel/views/account_payment_views.xml',


         # HR Expense Cancel
        'sh_hr_expense_cancel/security/hr_security.xml',
        'sh_hr_expense_cancel/data/server_action_data.xml',
        'sh_hr_expense_cancel/views/res_config_settings_views.xml',
        'sh_hr_expense_cancel/views/hr_expense_views.xml',
        'sh_hr_expense_cancel/views/hr_expense_sheet_views.xml',


         # Landed Cost Cancel
        'sh_landed_cost_cancel/security/stock_security.xml',
        'sh_landed_cost_cancel/data/server_action_data.xml',
        'sh_landed_cost_cancel/views/stock_config_settings_views.xml',
        'sh_landed_cost_cancel/views/landed_cost_views.xml',

         # POS Cancel
        # 'sh_pos_cancel/security/pos_security.xml',
        # 'sh_pos_cancel/data/server_action_data.xml',
        # 'sh_pos_cancel/views/pos_config_settings_views.xml',
        # 'sh_pos_cancel/views/pos_order_views.xml',


        # Purchase Cancel
        'sh_purchase_cancel/security/purchase_security.xml',
        'sh_purchase_cancel/data/server_action_data.xml',
        'sh_purchase_cancel/views/purchase_config_settings_views.xml',
        'sh_purchase_cancel/views/purchase_order_views.xml',

        # Sale Cancel
        'sh_sale_cancel/security/sale_security.xml',
        'sh_sale_cancel/data/server_action_data.xml',
        'sh_sale_cancel/views/sale_config_settings_views.xml',
        'sh_sale_cancel/views/sale_order_views.xml',
        
        # Stock Cancel
        'sh_stock_cancel/security/stock_security.xml',
        'sh_stock_cancel/data/server_action_data.xml',
        'sh_stock_cancel/views/res_config_settings_views.xml',
        'sh_stock_cancel/views/stock_picking_views.xml',
        'sh_stock_cancel/views/scrap_views.xml',

         # Mrp Cancel
         'sh_mrp_cancel/security/mrp_security.xml',
         'sh_mrp_cancel/data/server_action_data.xml',
         'sh_mrp_cancel/views/mrp_config_settings.xml',
         'sh_mrp_cancel/views/views.xml',

    ],

    "images": ['static/description/background.png', ],
    "auto_install": False,
    "installable": True,
    "price": "119.97",
    "currency": "EUR"
}

{
    'name': "My Custom Translations (TH)",
    'version': '18.0.1.0.0',
    'summary': """
        Overrides specific Thai translations for the Sale module.
    """,
    'description': """
        This module fixes and overrides Thai labels for:
        - sale.order (warehouse_id, expense_count)
    """,
    'author': "365 Infotech",
    'website': "https://www.365infotech.co.th/",
    'category': 'Sales/Sales',
    'license': 'LGPL-3',

    'depends': [
        'sale', 
        'sale_stock',      
        'purchase_stock',   
        'mrp',             
        'stock',
        'account',                  
        'account_auto_transfer',    
    ],

    'data': [
        
    ],
    
    'installable': True,
    'application': False, # ไม่ใช่ App หลัก
    'auto_install': False,
}
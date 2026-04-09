{
    'name': 'Payment Account Info Extension',
    'version': '1.0',
    'category': 'Accounting/Custom',
    'summary': 'ซ่อน Journal และเพิ่ม Account Code, Account Name ในหน้า Payment',
    'author': '365 Piyawat K.k',
    'depends': ['account'], 
    'data': [
        'views/payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
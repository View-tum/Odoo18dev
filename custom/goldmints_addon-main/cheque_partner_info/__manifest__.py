{
    'name': 'Cheque Partner Info Extension',
    'version': '1.0',
    'category': 'Accounting/Custom',
    'summary': 'เพิ่มคอลัมน์ Salesperson, Sales Region, และ Subregion ในหน้า Cheque',
    'author': '365 Piyawat K.k',
    'depends': ['base', 'cheque_management'], 
    'data': [
        'views/cheque_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
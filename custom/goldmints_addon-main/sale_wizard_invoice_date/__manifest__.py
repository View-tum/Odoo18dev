{
    'name': 'Sale Wizard Invoice Date',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'เพิ่มฟิลด์ Invoice Date ในหน้า Wizard ตอนกด Create Invoice จาก Sale Order',
    'description': """
        โมดูลนี้ทำการเพิ่มฟิลด์ Invoice Date ในออบเจกต์ sale.advance.payment.inv 
        เพื่อให้ User สามารถระบุวันที่ของ Invoice ได้ทันทีตั้งแต่ขั้นตอน Create Invoice
    """,
    'author': '365 Piyawat K.k',
    'depends': ['sale', 'sale_management', 'account', 'sale_stock'],
    'data': [
        'views/sale_advance_payment_inv_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
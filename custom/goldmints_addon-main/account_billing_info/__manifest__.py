{
    "name": "Account Billing Info Extension",
    "version": "18.0.0.1",
    "category": "Accounting/Custom",
    "summary": "เพิ่มคอลัมน์วันนัดชำระที่ใกล้ที่สุดในหน้า List ของ Billing และดึงวันที่วางบิลมาแสดงใน Billing Line",
    "author": "365 Piyawat K.k",
    "depends": [
        "account",
        "account_billing",
        # "account_billing_promised_date",
        "partner_payment_schedule",
    ],
    "data": [
        "views/billing_views.xml", 
        "views/account_move_views.xml"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}

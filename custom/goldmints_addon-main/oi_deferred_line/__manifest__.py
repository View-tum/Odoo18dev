{
    "name": "Deferred Config By Line",
    "summary": "ใช้ journal/account เลื่อนรับรู้จากบรรทัดเอกสารแทนตั้งค่าบริษัท และรองรับการสร้าง manual entry แยกตาม journal",
    "version": "18.0.1.1.0",
    "category": "Accounting",
    "author": "Goldmints",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_accountant",
        "account_reports"
    ],
    "data": [
        "views/account_move_views.xml",
        "views/product_template_views.xml"
    ],
    "installable": True,
}

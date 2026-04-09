{
    "name": "MRP Workcenter Single Job Lock",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "บล็อกไม่ให้ Work Center เดียวกันมี Work Order ทำงานซ้อน",
    "description": """
MRP Workcenter Single Job Lock

บังคับให้ 1 Work Center ทำงานได้ทีละ 1 Work Order เท่านั้น
หากมี Work Order อยู่ในสถานะกำลังทำงาน (progress) แล้ว
จะไม่สามารถเริ่ม Work Order ใหม่บน Work Center เดียวกันได้
จนกว่าจะจบ/หยุดงานเดิมก่อน
    """,
    "depends": ["mrp"],
    "data": [],
    "installable": True,
    "application": False,
}

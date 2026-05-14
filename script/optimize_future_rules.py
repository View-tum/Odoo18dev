import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 1. ปรับ Rule 'Transfer RM Replenish' (id=141) ให้ดึงจาก RM -> คลังลอย
# แทนที่จะเป็น Stock -> คลังลอย (เพื่อให้ต้นทางตรงกับ Rule หลัก)
rule_141 = env['stock.rule'].browse(141)
rm_loc = env['stock.location'].search([('name', '=', 'RM'), ('location_id.name', '=', 'Stock')], limit=1)

if rule_141.exists() and rm_loc:
    print("Updating Rule 141: %s" % rule_141.name)
    rule_141.write({
        'location_src_id': rm_loc.id,
        'procure_method': 'make_to_order' # บังคับให้ไปดึงจาก Stock มา RM อีกทีก่อน
    })

# 2. ปรับ Rule 'Transfer SM' (id=145) ให้ดึงจาก RM -> คลังลอย เช่นกัน
rule_145 = env['stock.rule'].browse(145)
if rule_145.exists() and rm_loc:
    print("Updating Rule 145: %s" % rule_145.name)
    rule_145.write({
        'location_src_id': rm_loc.id,
        'procure_method': 'make_to_order'
    })

# 3. เพิ่ม/ตรวจสอบ Rule ที่จะดึงของจาก Semi ไป RM (ถ้ายังไม่มี)
# เพื่อให้ Flow เป็น Semi -> RM -> คลังลอย
# (ในที่นี้ผมจะตรวจสอบ Rule ที่มีอยู่แล้วใน Route 'Auto Transfer RM')

env.cr.commit()
print("\n=== FUTURE RULES OPTIMIZED ===")

import json
from pathlib import Path

import requests


BASE = "http://10.0.0.14"
DB = "goldmints_uat"
USER = "admin"
PWD = "365@gmp"
OUT = Path("scratch/server14_task1596_rma_cn")
OUT.mkdir(parents=True, exist_ok=True)


session = requests.Session()
response = session.post(
    f"{BASE}/web/session/authenticate",
    json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"db": DB, "login": USER, "password": PWD},
    },
    timeout=30,
)
response.raise_for_status()


def call(model, method, args=None, kwargs=None):
    result = session.post(
        f"{BASE}/web/dataset/call_kw/{model}/{method}",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args or [],
                "kwargs": kwargs or {},
            },
        },
        timeout=60,
    )
    result.raise_for_status()
    payload = result.json()
    if payload.get("error"):
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False, indent=2))
    return payload.get("result")


thai_step = """<ol>
<li>เข้าเมนู RMA แล้วเลือกเอกสาร RMA ที่มีข้อมูลจริงในระบบ โดยไม่สร้างสินค้า ลูกค้า หรือ master data ใหม่</li>
<li>ตรวจสอบว่า RMA มีเอกสารขาย Delivery Order, Return Picking และ RMA Line ครบถ้วน</li>
<li>กด Smart Button <b>Refund Invoices / Credit Notes</b> จากหน้า RMA เพื่อเปิดใบลดหนี้ที่ระบบผูกไว้กับ RMA</li>
<li>ตรวจสอบใบลดหนี้ว่าเป็น Customer Credit Note, สถานะบัญชีถูกต้อง และยอดเงิน/ยอดคงเหลือถูกต้อง</li>
<li>กลับมาตรวจสอบหน้า RMA ว่าแสดงจำนวน Refund Invoice ถูกต้อง และ Return Picking เชื่อมกลับมายัง RMA</li>
<li>Regression: การเปิดใบลดหนี้จาก RMA ต้องไม่กระทบ flow การสร้าง/เปิด Credit Note ปกติของ Accounting</li>
</ol>"""

thai_expected = """<p><b>ผลลัพธ์ที่คาดหวัง</b></p>
<ul>
<li>ผู้ใช้สามารถเปิดใบลดหนี้จากหน้า RMA ได้โดยตรงผ่าน Smart Button</li>
<li>RMA ต้องเห็นจำนวน Refund Invoice/Credit Note ที่ถูกต้อง</li>
<li>Return Picking ต้องเชื่อมกับ RMA และอยู่ในสถานะที่ถูกต้อง</li>
<li>ใบลดหนี้ต้องเป็น Customer Credit Note, post ได้ตาม flow บัญชี และยอดคงเหลือถูกต้อง</li>
<li>ถ้าเป็น RMA Transform Return ระบบต้องมี field อ้างอิงกลับไป RMA/Transform Return ให้ตรวจสอบย้อนหลังได้</li>
</ul>
<p><b>ผลทดสอบจริง - PASS / มีข้อสังเกต (server14, 2026-06-13)</b></p>
<ul>
<li>ใช้ข้อมูลเดิมในระบบ: RMA0022 / RMATR/2026/06/000015 - Transform Return (crm.claim.ept:22)</li>
<li>RMA state = close, Sale Order = SOB-263089, Delivery = M-WH/OUT/03783, Return Picking = GMP/R-IN/00031</li>
<li>Return Picking GMP/R-IN/00031 state = done และมี claim_id กลับมาที่ RMA0022 ถูกต้อง</li>
<li>กด/open smart button Refund Invoices แล้วระบบเปิด CN ได้: CCND/26/06/00002 (account.move:70245)</li>
<li>CN เป็น move_type = out_refund, state = posted, payment_state = not_paid, amount_total = 15.00, amount_residual = 15.00</li>
<li>CN มี link กลับไป RMA ผ่าน rma_transform_claim_id = RMA0022 และ rma_transform_return_id = RMATR/2026/06/000015</li>
<li>ข้อสังเกต: field claim_id มาตรฐานของ rma_ept ว่าง แต่ flow transform ใช้ rma_transform_claim_id แทน ถ้ารายงาน/หน้าจอใดอิง claim_id ต้องปรับให้อ่าน field transform ด้วย</li>
<li>สรุป: flow เปิด CN จาก RMA ใช้งานได้ และตรวจสอบย้อนหลังได้ผ่าน field ของ transform flow</li>
</ul>"""

ok = call(
    "project.task",
    "write",
    [
        [1596],
        {
            "x_studio_test_steps": "PASS - เปิด CN จาก RMA ได้ และมี link กลับผ่าน transform fields",
            "x_studio_test_step": thai_step,
            "x_studio_expected_result": thai_expected,
        },
    ],
)
record = call(
    "project.task",
    "read",
    [[1596], ["id", "name", "x_studio_test_steps", "x_studio_test_step", "x_studio_expected_result"]],
)[0]
(OUT / "task1596_thai_update_readback.json").write_text(
    json.dumps({"write": ok, "record": record}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(json.dumps({"write": ok, "summary": record["x_studio_test_steps"]}, ensure_ascii=False))

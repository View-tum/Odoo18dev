import json
from pathlib import Path

import requests


BASE = "http://10.0.0.14"
DB = "goldmints_uat"
USER = "admin"
PWD = "365@gmp"
OUT = Path("scratch/server14_assigned_tester_mark_unimplemented")
OUT.mkdir(parents=True, exist_ok=True)


thai_step = """<ol>
<li>เข้าเมนู Advance และเปิด flow การจ่ายเงิน/ซื้อดราฟท์จากเอกสาร Advance ที่มีอยู่ในระบบ</li>
<li>ตรวจสอบ wizard/payment popup ว่ามี Payment Method ประเภท Bank Draft หรือไม่</li>
<li>ตรวจสอบว่าหน้าจอมี field สำหรับเลขดราฟท์, ธนาคาร, สาขา, วันที่ดราฟท์ และสามารถสร้าง audit record เหมือน Cheque ได้หรือไม่</li>
<li>ตรวจสอบ source code/local module ว่า Advance ส่งค่า bank draft เข้า action_confirm หรือไม่</li>
<li>ถ้า function ยังไม่ implement ให้หยุด test และ mark เป็น Blocked/Not Implemented ไม่สร้างเอกสารจริง</li>
</ol>"""

thai_expected = """<p><b>ผลลัพธ์ที่คาดหวัง</b></p>
<ul>
<li>Advance ต้องรองรับการซื้อดราฟท์ธนาคารเหมือน Cheque</li>
<li>ต้องมี field สำหรับ Bank Draft Number, Bank, Branch, Draft Date และสร้าง instrument/audit record ได้</li>
<li>การ post payment ต้องสร้าง accounting entry ถูกต้อง และไม่กระทบ Cheque flow เดิม</li>
</ul>
<p><b>ผลทดสอบจริง - BLOCKED / NOT IMPLEMENTED (2026-06-13)</b></p>
<ul>
<li>ตรวจ local code แล้วพบว่า wizard <code>advance.cash.payment.wizard</code> ยังมีเฉพาะ Cheque fields: cheque_id, cheque_date, cheque_number_in, cheque_bank_in, cheque_branch_in</li>
<li>ยังไม่พบ field/logic ใน production wizard สำหรับ <code>is_bank_draft_method</code>, <code>bank_draft_number</code>, <code>bank_draft_bank_id</code>, <code>bank_draft_branch</code>, <code>bank_draft_date</code></li>
<li>model <code>advance.cash.log</code> ยังไม่มี logic สร้าง Bank Draft instrument จาก payment_data; code ปัจจุบัน handle เฉพาะ Cheque</li>
<li>มี test file <code>easy_advance_cash/tests/test_advance_bank_draft.py</code> ที่คาดหวัง bank draft แต่ implementation หลักยังไม่รองรับตาม test นั้น</li>
<li>สรุป: ยังไม่สามารถทำ UAT end-to-end ได้ เพราะ function ซื้อดราฟท์บน Advance ยัง implement ไม่ครบ ต้องส่งกลับ Dev ก่อน</li>
</ul>"""


def call(session, model, method, args=None, kwargs=None):
    response = session.post(
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
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False, indent=2))
    return payload.get("result")


session = requests.Session()
auth = session.post(
    f"{BASE}/web/session/authenticate",
    json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"db": DB, "login": USER, "password": PWD},
    },
    timeout=30,
)
auth.raise_for_status()

summary = "BLOCKED - Advance bank draft function not implemented yet"
write_ok = call(
    session,
    "project.task",
    "write",
    [
        [1622],
        {
            "x_studio_test_steps": summary,
            "x_studio_test_step": thai_step,
            "x_studio_expected_result": thai_expected,
        },
    ],
)
body = """<p><b>QA Test Update 2026-06-13</b></p>
<p>รายการ Advance ซื้อดราฟท์ถูก mark เป็น BLOCKED / NOT IMPLEMENTED เนื่องจาก implementation ปัจจุบันยังรองรับเฉพาะ Cheque fields และยังไม่มี Bank Draft fields/logic ใน Advance payment wizard</p>"""
message = call(session, "project.task", "message_post", [[1622]], {"body": body})
record = call(
    session,
    "project.task",
    "read",
    [[1622], ["id", "name", "x_studio_test_steps", "write_date"]],
)[0]
result = {"write": write_ok, "record": record, "message": message}
(OUT / "task1622_marked_unimplemented.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False, indent=2))

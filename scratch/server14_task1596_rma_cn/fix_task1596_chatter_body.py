import json
from pathlib import Path

import requests


BASE = "http://10.0.0.14"
DB = "goldmints_uat"
USER = "admin"
PWD = "365@gmp"
OUT = Path("scratch/server14_task1596_rma_cn")

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


body = """<p><b>QA Test Update 2026-06-13</b></p>
<p>อัปเดต Test Step เป็นภาษาไทย และทดสอบ RMA/CN ด้วยข้อมูลจริงบน server14 แล้ว</p>
<ul>
<li>RMA: RMA0022 / RMATR/2026/06/000015 - Transform Return</li>
<li>CN: CCND/26/06/00002 เปิดได้จาก Smart Button Refund Invoices บน RMA</li>
<li>ผล: PASS - เปิด CN จาก RMA ได้ และ CN มี link กลับผ่าน rma_transform_claim_id / rma_transform_return_id</li>
<li>ข้อสังเกต: field claim_id มาตรฐานยังว่าง เพราะ transform flow ใช้ field rma_transform_claim_id แทน ถ้ารายงานหรือหน้าจอใดอิง claim_id ต้องรองรับ field transform ด้วย</li>
</ul>"""

ok = call("mail.message", "write", [[267357], {"body": body}])
message = call("mail.message", "read", [[267357], ["id", "body", "attachment_ids"]])[0]
(OUT / "task1596_chatter_body_fixed.json").write_text(
    json.dumps({"write": ok, "message": message}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(json.dumps({"write": ok, "attachment_ids": message["attachment_ids"]}, ensure_ascii=False))

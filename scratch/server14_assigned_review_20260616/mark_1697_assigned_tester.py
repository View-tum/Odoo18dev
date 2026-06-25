import base64
import json
from pathlib import Path

import requests


URL = "http://10.0.0.14"
DB = "goldmints_uat"
USER = "admin"
PASSWORD = "365@gmp"
TASK_ID = 1697
SCREENSHOT = Path(__file__).with_name("screenshots") / "task1697_asset_list_last_post_depreciation_date.png"


def connect():
    session = requests.Session()
    response = session.post(
        f"{URL}/web/session/authenticate",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"db": DB, "login": USER, "password": PASSWORD},
        },
        timeout=30,
    )
    response.raise_for_status()
    result = response.json().get("result") or {}
    if not result.get("uid"):
        raise RuntimeError("Authentication failed")
    return session, result["uid"]


def call(session, model, method, *args, **kwargs):
    response = session.post(
        f"{URL}/web/dataset/call_kw/{model}/{method}",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": list(args),
                "kwargs": kwargs,
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False, default=str))
    return payload.get("result")


def main():
    if not SCREENSHOT.exists():
        raise RuntimeError(f"Screenshot not found: {SCREENSHOT}")
    session, uid = connect()
    task = call(
        session,
        "project.task",
        "read",
        [TASK_ID],
        ["project_id", "stage_id", "name"],
    )[0]
    stages = call(
        session,
        "project.task.type",
        "search_read",
        [("name", "=", "06) Assigned Tester"), ("project_ids", "in", [task["project_id"][0]])],
        fields=["id", "name"],
        limit=1,
    )
    if not stages:
        raise RuntimeError("Stage 06) Assigned Tester not found")
    stage_id = stages[0]["id"]

    test_step = """1. เข้าเมนู Accounting > Accounting > Assets
2. เปิดหน้า Assets แบบ List view
3. ตรวจสอบว่ามีคอลัมน์ Last Post Depreciation Date แสดงบน list
4. ตรวจสอบรายการ asset ที่มี depreciation posted แล้ว เช่น Crane 5 ton Xspan 6 M. หรือ asset อื่นที่มี posted depreciation entry
5. ตรวจสอบวันที่ในคอลัมน์ Last Post Depreciation Date ต้องแสดงวันที่ posted depreciation ล่าสุดของ asset นั้น"""

    expected = """หน้ารายการ Assets ต้องแสดงคอลัมน์ Last Post Depreciation Date
ถ้า asset มีรายการ depreciation ที่ posted แล้ว ระบบต้องแสดงวันที่ posted ล่าสุด
ถ้า asset ยังไม่มี depreciation ที่ posted แล้ว คอลัมน์นี้ต้องว่าง
การเพิ่มคอลัมน์ต้องไม่กระทบข้อมูลมูลค่าสินทรัพย์, depreciation board, หรือสถานะ asset เดิม"""

    summary = "PASS - Server 14 มี field และ list column Last Post Depreciation Date แล้ว ตรวจผ่าน UI จริงและแนบ screenshot"

    call(
        session,
        "project.task",
        "write",
        [TASK_ID],
        {
            "stage_id": stage_id,
            "x_studio_test_steps": summary,
            "x_studio_test_step": test_step,
            "x_studio_expected_result": expected,
        },
    )

    attachment_id = call(
        session,
        "ir.attachment",
        "create",
        {
            "name": SCREENSHOT.name,
            "res_model": "project.task",
            "res_id": TASK_ID,
            "type": "binary",
            "mimetype": "image/png",
            "datas": base64.b64encode(SCREENSHOT.read_bytes()).decode("ascii"),
        },
    )
    body = """<p><b>Assigned to Tester - ผลทดสอบ UI</b></p>
<p>ตรวจสอบบน Server 14 แล้ว: หน้า Accounting &gt; Assets แบบ List view แสดงคอลัมน์ <b>Last Post Depreciation Date</b> ได้จริง และมีข้อมูลวันที่สำหรับ asset ที่มี posted depreciation entry.</p>
<p>แนบภาพหน้าจอผลทดสอบไว้ในข้อความนี้แล้ว</p>"""
    call(
        session,
        "project.task",
        "message_post",
        [TASK_ID],
        body=body,
        attachment_ids=[attachment_id],
        subtype_xmlid="mail.mt_note",
    )
    print(json.dumps({"task_id": TASK_ID, "stage_id": stage_id, "attachment_id": attachment_id}, ensure_ascii=False))


if __name__ == "__main__":
    main()

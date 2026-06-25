import base64
import json
from pathlib import Path

import requests


URL = "http://10.0.0.14"
DB = "goldmints_uat"
USER = "admin"
PASSWORD = "365@gmp"
TASK_ID = 1690
SCREENSHOT = Path(__file__).with_name("screenshots") / "task1690_transfer_links_two_mos.png"


def connect():
    session = requests.Session()
    response = session.post(
        f"{URL}/web/session/authenticate",
        json={"jsonrpc": "2.0", "method": "call", "params": {"db": DB, "login": USER, "password": PASSWORD}},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json().get("result") or {}
    if not result.get("uid"):
        raise RuntimeError("Authentication failed")
    return session


def call(session, model, method, *args, **kwargs):
    response = session.post(
        f"{URL}/web/dataset/call_kw/{model}/{method}",
        json={"jsonrpc": "2.0", "method": "call", "params": {"model": model, "method": method, "args": list(args), "kwargs": kwargs}},
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
    session = connect()
    task = call(session, "project.task", "read", [TASK_ID], ["project_id", "name"])[0]
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

    test_step = """1. เปิด Inventory > Transfers
2. ค้นหา Internal Transfer เลขที่ GMP/TRPL/00059
3. เปิดเอกสารและตรวจสอบ Source Document ว่ามี MO ทั้ง GMP/MOPL/00169 และ GMP/MOPL/00170
4. ตรวจสอบ smart button Manufacturing ด้านบน
5. กด smart button Manufacturing และตรวจว่าระบบเปิดรายการ MO ที่เกี่ยวข้องได้ 2 ใบ"""

    expected = """Internal Transfer ที่ merge จาก MO หลายใบต้อง link กลับไปหา MO ได้ครบทุกใบ
ตัวอย่าง GMP/TRPL/00059 ต้องแสดง Manufacturing = 2
Source Document ต้องระบุทั้ง GMP/MOPL/00169 และ GMP/MOPL/00170
การแก้ไขต้องไม่ทำให้ stock move, demand quantity, source/destination location หรือสถานะ transfer เดิมเปลี่ยนเอง"""

    summary = "PASS - Server 14 แสดง Manufacturing smart button = 2 สำหรับ GMP/TRPL/00059 และ origin มี MO ครบ"

    call(
        session,
        "project.task",
        "write",
        [TASK_ID],
        {"stage_id": stage_id, "x_studio_test_steps": summary, "x_studio_test_step": test_step, "x_studio_expected_result": expected},
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
<p>ตรวจสอบบน Server 14 แล้ว: Internal Transfer <b>GMP/TRPL/00059</b> แสดง smart button <b>Manufacturing = 2</b> และ Source Document มี MO ทั้งสองใบที่ merge มา.</p>
<p>แนบภาพหน้าจอผลทดสอบไว้ในข้อความนี้แล้ว</p>"""
    call(session, "project.task", "message_post", [TASK_ID], body=body, attachment_ids=[attachment_id], subtype_xmlid="mail.mt_note")
    print(json.dumps({"task_id": TASK_ID, "stage_id": stage_id, "attachment_id": attachment_id}, ensure_ascii=False))


if __name__ == "__main__":
    main()

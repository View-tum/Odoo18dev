const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE = "http://10.0.0.14";
const DB = "goldmints_uat";
const USER = "admin";
const PASSWORD = "365@gmp";
const OUT_DIR = path.resolve("output/playwright/server14_assigned_tester_uat");
const RUN_ID = `SERVER14-UAT-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;

fs.mkdirSync(OUT_DIR, { recursive: true });

class OdooRpc {
  constructor() {
    this.cookie = "";
  }

  async post(route, payload) {
    const headers = { "Content-Type": "application/json" };
    if (this.cookie) headers.Cookie = this.cookie;
    const response = await fetch(`${BASE}${route}`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    const setCookie = response.headers.get("set-cookie");
    if (setCookie) {
      const first = setCookie.split(";")[0];
      if (!this.cookie.includes(first.split("=")[0])) {
        this.cookie = this.cookie ? `${this.cookie}; ${first}` : first;
      } else {
        this.cookie = this.cookie
          .split("; ")
          .map((part) => (part.startsWith(first.split("=")[0] + "=") ? first : part))
          .join("; ");
      }
    }
    const json = await response.json();
    if (json.error) {
      const data = json.error.data || {};
      throw new Error(data.message || json.error.message || JSON.stringify(json.error));
    }
    return json.result;
  }

  async login() {
    return this.post("/web/session/authenticate", {
      jsonrpc: "2.0",
      params: { db: DB, login: USER, password: PASSWORD },
    });
  }

  async call(model, method, args = [], kwargs = {}) {
    return this.post(`/web/dataset/call_kw/${model}/${method}`, {
      jsonrpc: "2.0",
      params: { model, method, args, kwargs },
    });
  }

  async fields(model) {
    return this.call(model, "fields_get", [], { attributes: ["string", "type", "relation", "store"] });
  }

  async searchRead(model, domain, fields, opts = {}) {
    return this.call(model, "search_read", [domain], { fields, ...opts });
  }

  async read(model, ids, fields) {
    return this.call(model, "read", [ids, fields]);
  }

  async create(model, vals, context = undefined) {
    return this.call(model, "create", [vals], context ? { context } : {});
  }

  async write(model, ids, vals, context = undefined) {
    return this.call(model, "write", [ids, vals], context ? { context } : {});
  }

  async button(model, method, ids, context = undefined) {
    return this.call(model, method, [ids], context ? { context } : {});
  }
}

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function htmlList(items) {
  return `<ul>${items.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>`;
}

async function attachScreens(rpc, taskId, screenshotPaths, body) {
  const attachmentIds = [];
  for (const screenshotPath of screenshotPaths.filter(Boolean)) {
    const datas = fs.readFileSync(screenshotPath).toString("base64");
    const attachmentId = await rpc.create("ir.attachment", {
      name: path.basename(screenshotPath),
      res_model: "project.task",
      res_id: taskId,
      type: "binary",
      datas,
      mimetype: "image/png",
    });
    attachmentIds.push(attachmentId);
  }
  return rpc.call("project.task", "message_post", [[taskId]], {
    body,
    message_type: "comment",
    subtype_xmlid: "mail.mt_note",
    attachment_ids: attachmentIds,
  });
}

async function screenshotRecord(page, model, id, label) {
  const safe = label.replace(/[^a-zA-Z0-9_.-]+/g, "_");
  const file = path.join(OUT_DIR, `${RUN_ID}_${safe}.png`);
  await page.goto(`${BASE}/web#id=${id}&model=${encodeURIComponent(model)}&view_type=form`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  await page.locator(".o_form_view, .o_action_manager").first().waitFor({ timeout: 20000 }).catch(() => {});
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function postTask(rpc, taskId, title, status, steps, expected, actual, screenshots = []) {
  const body = `
    <p><strong>${esc(title)}</strong></p>
    <p><strong>Run:</strong> ${esc(RUN_ID)} | <strong>Result:</strong> ${esc(status)}</p>
    <p><strong>Test Steps</strong></p>${htmlList(steps)}
    <p><strong>Expected Results</strong></p>${htmlList(expected)}
    <p><strong>Actual Results</strong></p>${htmlList(actual)}
  `;
  await attachScreens(rpc, taskId, screenshots, body);
}

function m2oName(value) {
  return Array.isArray(value) ? value[1] : value || "";
}

function sum(items, getter) {
  return items.reduce((acc, item) => acc + Number(getter(item) || 0), 0);
}

async function test1693(rpc, page) {
  const taskId = 1693;
  const po = (await rpc.searchRead("purchase.order", [["name", "=", "P00125"]], ["id", "name", "partner_id", "order_line", "billing_note_ids", "invoice_ids"], { limit: 1 }))[0];
  if (!po) throw new Error("P00125 not found");
  const wizardId = await rpc.create("purchase.order.status.report.wizard", {
    vendor_id: po.partner_id[0],
    product_id: 8690,
    date_from: "2026-06-01",
    date_to: "2026-06-30",
    state: "purchase",
  });
  await rpc.button("purchase.order.status.report.wizard", "button_preview", [wizardId]);
  const wizard = (await rpc.read("purchase.order.status.report.wizard", [wizardId], ["line_ids"]))[0];
  const lineFields = ["id", "order_id", "po_line_id", "product_id", "qty", "qty_received", "subtotal", "is_header", "is_billable", "is_already_billed", "billing_note_status", "line_type"];
  const lines = await rpc.read("purchase.order.status.report.wizard.line", wizard.line_ids, lineFields);
  const targetLines = lines.filter((line) => line.order_id && line.order_id[0] === po.id && line.line_type === "po" && line.is_billable);
  if (!targetLines.length) throw new Error("P00125 fixed asset line is not billable in PO status wizard");
  await rpc.write("purchase.order.status.report.wizard.line", [targetLines[0].id], { is_selected: true });
  const action = await rpc.button("purchase.order.status.report.wizard", "action_create_billing_note", [wizardId]);
  const bnId = action.res_id;
  if (!bnId) throw new Error("Billing note action did not return res_id");
  await rpc.button("vendor.billing.note", "action_confirm", [bnId]);
  const bn = (await rpc.read("vendor.billing.note", [bnId], ["name", "state", "partner_id", "amount_total", "line_ids", "purchase_ids"]))[0];
  const wizShot = await screenshotRecord(page, "purchase.order.status.report.wizard", wizardId, "1693_po_status_wizard");
  const bnShot = await screenshotRecord(page, "vendor.billing.note", bnId, "1693_fixed_asset_bn");
  await postTask(
    rpc,
    taskId,
    "UAT 1693 - Fixed Asset PO Status Report to Billing Note",
    bn.state === "confirmed" && bn.line_ids.length ? "PASS" : "FAIL",
    [
      "เปิด Purchase Order Status Report ด้วย Vendor ร้านค้า บอส, Product Injection Machine, ช่วงวันที่ 01/06/2026-30/06/2026",
      "กด Preview และเลือก PO P00125",
      "กด Create Billing Note และ Confirm Billing Note",
      "ตรวจ backend ว่า BN มี line จาก P00125 แม้ qty_received = 0",
    ],
    [
      "P00125 ต้องขึ้นเป็น billable line เพราะเป็น fixed asset PO",
      "Create Billing Note ต้องสร้างเอกสารจริงได้",
      "Billing Note ต้องอยู่สถานะ Confirmed และมี Purchase Order link กลับไป P00125",
    ],
    [
      `พบ line ใน wizard ${targetLines.length} line: qty=${targetLines[0].qty}, qty_received=${targetLines[0].qty_received}, subtotal=${targetLines[0].subtotal}`,
      `สร้าง Billing Note ${bn.name} id=${bnId}, state=${bn.state}, total=${bn.amount_total}`,
      `purchase_ids=${bn.purchase_ids.map((id) => id).join(", ")}, line_count=${bn.line_ids.length}`,
    ],
    [wizShot, bnShot]
  );
  return { bnId, wizardId, lines: targetLines, bn };
}

async function test1665(rpc, page) {
  const taskId = 1665;
  const moveIds = [69732, 69691, 69854];
  const moves = await rpc.read("account.move", moveIds, ["id", "name", "move_type", "state", "partner_id", "amount_total", "amount_residual", "vendor_billing_note_id"]);
  if (moves.some((move) => move.vendor_billing_note_id)) throw new Error("Selected APD/CN already linked to a billing note");
  const action = await rpc.button("account.move", "action_create_vendor_billing_note", moveIds);
  const bnId = action.res_id;
  await rpc.button("vendor.billing.note", "action_confirm", [bnId]);
  const fields = ["name", "state", "partner_id", "amount_vendor_bills", "amount_credit_notes", "amount_net_due", "amount_residual_net_due", "billing_source", "bill_ids", "payment_state"];
  const bn = (await rpc.read("vendor.billing.note", [bnId], fields))[0];
  const net = Number(bn.amount_residual_net_due || 0);
  const shot = await screenshotRecord(page, "vendor.billing.note", bnId, "1665_vendor_bill_cn_bn");
  await postTask(
    rpc,
    taskId,
    "UAT 1665 - Vendor Billing Note from APD + Credit Note",
    Math.abs(net) < 0.01 && bn.billing_source === "existing_bills" ? "PASS" : "FAIL",
    [
      "เลือก APD/26/05/00043, APD/26/05/00041 และ VCND/26/06/00003 ของ vendor เดียวกัน",
      "สร้าง Vendor Billing Note จากเอกสาร APD/CN",
      "Confirm Billing Note",
      "ตรวจ backend ว่า vendor bill และ credit note ถูกผูกเข้า BN และยอดสุทธิเป็น 0",
    ],
    [
      "BN ต้องรับทั้ง Vendor Bill และ Vendor Credit Note ได้",
      "ยอด Vendor Bills 40,660 และ Credit Notes 40,660 ต้องหักล้างกัน",
      "Open Balance / Amount Due ต้องไม่เกิด Payment Difference",
    ],
    [
      `สร้าง Billing Note ${bn.name} id=${bnId}, source=${bn.billing_source}, state=${bn.state}`,
      `bill_ids=${bn.bill_ids.join(", ")}`,
      `vendor_bills=${bn.amount_vendor_bills}, credit_notes=${bn.amount_credit_notes}, net_due=${bn.amount_net_due}, open_balance=${bn.amount_residual_net_due}, payment_state=${bn.payment_state}`,
    ],
    [shot]
  );
  return { bnId, bn, moves };
}

async function test1667(rpc, page) {
  const taskId = 1667;
  const returnPickingId = 10591;
  const billId = 69275;
  const before = (await rpc.read("stock.picking", [returnPickingId], ["name", "vendor_credit_note_state", "vendor_credit_note_count", "vendor_credit_note_ids"]))[0];
  let creditNoteId = false;
  let status = "PASS";
  const actual = [`ก่อนทดสอบ ${before.name}: state=${before.vendor_credit_note_state}, count=${before.vendor_credit_note_count}`];
  try {
    const bill = (await rpc.read("account.move", [billId], ["journal_id", "name", "state", "move_type"]))[0];
    const reversalId = await rpc.create(
      "account.move.reversal",
      {
        reason: `${RUN_ID} Vendor Return CN`,
        date: "2026-06-18",
        journal_id: bill.journal_id[0],
      },
      { active_model: "account.move", active_ids: [billId], active_id: billId }
    );
    await rpc.write("account.move.reversal", [reversalId], { return_picking_ids: [[6, 0, [returnPickingId]]] }, { active_model: "account.move", active_ids: [billId], active_id: billId });
    const action = await rpc.button("account.move.reversal", "reverse_moves", [reversalId], { active_model: "account.move", active_ids: [billId], active_id: billId });
    creditNoteId = action.res_id || (action.domain && action.domain[0] && action.domain[0][2] && action.domain[0][2][0]);
    if (!creditNoteId) {
      const reversal = (await rpc.read("account.move.reversal", [reversalId], ["new_move_ids"]))[0];
      creditNoteId = reversal.new_move_ids[0];
    }
    await rpc.write("account.move", [creditNoteId], { invoice_date: "2026-06-18" });
    await rpc.button("account.move", "action_post", [creditNoteId]);
  } catch (err) {
    status = "FAIL";
    actual.push(`สร้าง/post CN ไม่สำเร็จ: ${err.message}`);
  }
  const after = (await rpc.read("stock.picking", [returnPickingId], ["name", "vendor_credit_note_state", "vendor_credit_note_count", "vendor_credit_note_ids"]))[0];
  if (status === "PASS" && after.vendor_credit_note_state !== "posted") status = "FAIL";
  actual.push(`หลังทดสอบ ${after.name}: state=${after.vendor_credit_note_state}, count=${after.vendor_credit_note_count}, CN=${after.vendor_credit_note_ids.join(", ")}`);
  if (creditNoteId) {
    const cn = (await rpc.read("account.move", [creditNoteId], ["name", "state", "move_type", "return_picking_ids", "amount_total"]))[0];
    actual.push(`Credit Note ${cn.name}: state=${cn.state}, move_type=${cn.move_type}, return_picking_ids=${cn.return_picking_ids.join(", ")}, total=${cn.amount_total}`);
  }
  const pickShot = await screenshotRecord(page, "stock.picking", returnPickingId, "1667_vendor_return");
  const cnShot = creditNoteId ? await screenshotRecord(page, "account.move", creditNoteId, "1667_vendor_credit_note") : null;
  await postTask(
    rpc,
    taskId,
    "UAT 1667 - Vendor Return linked to Vendor Credit Note",
    status,
    [
      "เปิด Vendor Return GMP/R-OUT/00004 ที่ยังเป็น To Credit Note",
      "Reverse Vendor Bill APD/26/05/00022 และเลือก Return Picking ใน wizard",
      "Post Vendor Credit Note",
      "ตรวจ smart link/status ฝั่ง stock.picking และ return_picking_ids ฝั่ง account.move",
    ],
    [
      "Vendor Return ต้องเลือกเข้า CN ได้",
      "CN ต้องมี return_picking_ids กลับไปหา Return Picking",
      "Vendor Return status ต้องเปลี่ยนเป็น Credit Note Issued เมื่อ CN Posted",
    ],
    actual,
    [pickShot, cnShot].filter(Boolean)
  );
  return { creditNoteId, before, after, status };
}

async function test1622(rpc, page) {
  const taskId = 1622;
  const draftNo = `UAT-BD-${RUN_ID.slice(-14)}`;
  const advId = await rpc.create("advance.cash.log", {
    transaction_type: "return",
    employee_id: 1,
    description: `${RUN_ID} Return Advance Bank Draft`,
    amount: 1.0,
    journal_id: 65,
    accountant_id: 2,
    return_payment_journal_id: 52,
    return_payment_method_line_id: 132,
    bank_draft_number: draftNo,
    bank_draft_bank_id: 14,
    bank_draft_branch: "UAT Branch",
    bank_draft_date: "2026-06-18",
  });
  await rpc.button("advance.cash.log", "action_submit", [advId]);
  await rpc.button("advance.cash.log", "action_manager_approve", [advId]);
  await rpc.button("advance.cash.log", "action_approve", [advId]);
  const approved = (await rpc.read("advance.cash.log", [advId], ["name", "state", "bank_draft_id", "bank_draft_number", "return_payment_journal_id", "return_payment_method_line_id", "is_return_bank_draft_method"]))[0];
  await rpc.button("advance.cash.log", "action_confirm", [advId]);
  const posted = (await rpc.read("advance.cash.log", [advId], ["name", "state", "bank_draft_id", "move_id", "amount"]))[0];
  const draft = posted.bank_draft_id ? (await rpc.read("cheque.inbound.outbound", [posted.bank_draft_id[0]], ["name", "instrument_type", "cheque_type", "amount", "cheque_bank_branch", "advance_cash_id", "cheque_journal_entry_id"]))[0] : null;
  const advShot = await screenshotRecord(page, "advance.cash.log", advId, "1622_return_advance");
  const bdShot = draft ? await screenshotRecord(page, "cheque.inbound.outbound", posted.bank_draft_id[0], "1622_bank_draft") : null;
  await postTask(
    rpc,
    taskId,
    "UAT 1622 - Return Advance with Bank Draft",
    posted.state === "posted" && draft && draft.instrument_type === "bank_draft" ? "PASS" : "FAIL",
    [
      "สร้าง Return Advance ด้วย employee Administrator และ amount 1.00",
      "กรอก Bank Draft Number, Issue Bank, Branch, Date ก่อน submit/approve",
      "Submit, Manager Approve, Account Approve",
      "ตรวจว่า Bank Draft ถูกสร้างตอน Account Approve แล้ว Confirm เพื่อ post journal entry",
    ],
    [
      "Return Advance ต้องบังคับข้อมูล Bank Draft เมื่อใช้ payment method Bank Draft",
      "หลัง Account Approve ต้องมี Bank Draft link",
      "หลัง Confirm ต้องได้ Journal Entry และ Bank Draft ต้อง link กลับ Advance",
    ],
    [
      `หลัง Account Approve: ${approved.name}, state=${approved.state}, bank_draft=${m2oName(approved.bank_draft_id)}, method=${m2oName(approved.return_payment_method_line_id)}`,
      `หลัง Confirm: state=${posted.state}, move=${m2oName(posted.move_id)}, amount=${posted.amount}`,
      draft ? `Bank Draft ${draft.name}: type=${draft.instrument_type}, cheque_type=${draft.cheque_type}, amount=${draft.amount}, branch=${draft.cheque_bank_branch}, advance=${m2oName(draft.advance_cash_id)}, journal_entry=${m2oName(draft.cheque_journal_entry_id)}` : "ไม่พบ Bank Draft",
    ],
    [advShot, bdShot].filter(Boolean)
  );
  return { advId, posted, draft };
}

async function test1684(rpc, page) {
  const taskId = 1684;
  const contractId = await rpc.create("contract.document", {
    name: `${RUN_ID} Contract Reminder`,
    partner_id: 70301,
    user_id: 2,
    date_start: "2026-06-18",
    date_end: "2026-06-25",
    reminder_days: "7",
    state: "open",
  });
  await rpc.button("contract.document", "send_reminder", [contractId]);
  const contract = (await rpc.read("contract.document", [contractId], ["name", "state", "date_end", "remaining_days", "reminder_days", "message_ids"]))[0];
  const messages = contract.message_ids.length ? await rpc.read("mail.message", contract.message_ids.slice(0, 5), ["body", "date"]) : [];
  const messageText = messages.map((m) => String(m.body || "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim()).join(" | ");
  const shot = await screenshotRecord(page, "contract.document", contractId, "1684_contract_reminder");
  await postTask(
    rpc,
    taskId,
    "UAT 1684 - Contract Expiry Reminder Trigger",
    messageText.includes("Contract reminder") || messageText.includes("Failed to send contract reminder") ? "PASS_WITH_ENV_NOTICE" : "FAIL",
    [
      "สร้าง Contract ทดสอบด้วย partner DENKI SHOJI CO.,LTD. และ user Administrator",
      "ตั้ง End Date = 25/06/2026 และ Reminder Before = 7 วัน",
      "เรียก Run Daily Reminder Check",
      "ตรวจ chatter และ backend message_ids",
    ],
    [
      "เมื่อ remaining_days เท่ากับ reminder_days ระบบต้อง trigger reminder",
      "ใน UAT นี้ mail server เป็น neutralization/invalid จึงไม่ควรส่ง email จริงออกนอกระบบ",
      "ถ้าส่งจริงไม่ได้เพราะ mail server neutralized ต้องมีข้อความ failure ใน chatter ไม่ใช่ silent fail",
    ],
    [
      `${contract.name}: state=${contract.state}, date_end=${contract.date_end}, remaining_days=${contract.remaining_days}, reminder_days=${contract.reminder_days}`,
      `Chatter latest: ${messageText || "no message"}`,
    ],
    [shot]
  );
  return { contractId, contract, messageText };
}

async function test1596(rpc, page) {
  const taskId = 1596;
  const rmaId = 6;
  const rma = (await rpc.read("rma.transform.return", [rmaId], ["name", "state", "return_picking_id", "credit_note_id", "credit_note_ids", "invoice_id"]))[0];
  const cnId = rma.credit_note_id ? rma.credit_note_id[0] : (rma.credit_note_ids || [])[0];
  const cn = cnId ? (await rpc.read("account.move", [cnId], ["name", "state", "move_type", "invoice_origin", "amount_total"]))[0] : null;
  const rmaShot = await screenshotRecord(page, "rma.transform.return", rmaId, "1596_rma");
  const cnShot = cnId ? await screenshotRecord(page, "account.move", cnId, "1596_rma_cn") : null;
  await postTask(
    rpc,
    taskId,
    "UAT 1596 - CN RMA link check",
    rma.state === "done" && cn && cn.move_type === "out_refund" ? "PASS" : "BLOCKED_OR_FAIL",
    [
      "เปิด RMA Transform Return RMATR/2026/05/000006",
      "ตรวจ Return Picking และ Credit Note link จากหน้า RMA",
      "เปิด Credit Note ที่ link กลับจาก RMA",
      "ตรวจ backend state และ move_type",
    ],
    [
      "RMA ที่ done ต้องมี Return Picking และ Credit Note link",
      "Credit Note ต้องเป็น Customer Credit Note และเปิดจาก smart link/field ได้",
    ],
    [
      `RMA ${rma.name}: state=${rma.state}, return_picking=${m2oName(rma.return_picking_id)}, credit_note=${m2oName(rma.credit_note_id) || (rma.credit_note_ids || []).join(", ")}`,
      cn ? `CN ${cn.name}: state=${cn.state}, move_type=${cn.move_type}, origin=${cn.invoice_origin || ""}, total=${cn.amount_total}` : "ไม่พบ Credit Note link",
    ],
    [rmaShot, cnShot].filter(Boolean)
  );
  return { rma, cn };
}

async function test1703(rpc, page) {
  const taskId = 1703;
  const mo = (await rpc.searchRead("mrp.production", [["name", "=", "GMP/MOPL/00193"]], ["id", "name", "state", "origin", "purchase_order_count", "procurement_group_id", "move_raw_ids"], { limit: 1 }))[0];
  const pos = await rpc.searchRead("purchase.order", [["origin", "ilike", "GMP/MOPL/00193"]], ["id", "name", "origin", "state", "partner_id", "amount_total"], { limit: 10 });
  const moShot = await screenshotRecord(page, "mrp.production", mo.id, "1703_mo_po_smart_button");
  const poShot = pos[0] ? await screenshotRecord(page, "purchase.order", pos[0].id, "1703_auto_po") : null;
  await postTask(
    rpc,
    taskId,
    "UAT 1703 - Auto PO smart button from MO",
    mo.purchase_order_count >= 1 && pos.length >= 1 ? "PASS" : "FAIL",
    [
      "เปิด MO GMP/MOPL/00193",
      "ตรวจ backend purchase_order_count",
      "ค้นหา PO ที่ origin มี GMP/MOPL/00193",
      "เปิด PO จากผลที่พบเพื่อตรวจ link",
    ],
    [
      "MO ที่ auto enabled และเปิด PO จาก RM shortage ต้องมี smart button/จำนวน PO",
      "PO ต้องมี origin อ้างอิง MO ต้นทาง",
    ],
    [
      `MO ${mo.name}: state=${mo.state}, purchase_order_count=${mo.purchase_order_count}, group=${m2oName(mo.procurement_group_id)}`,
      `PO found=${pos.map((po) => `${po.name}(${po.state})`).join(", ") || "none"}`,
    ],
    [moShot, poShot].filter(Boolean)
  );
  return { mo, pos };
}

async function test1701(rpc, page) {
  const taskId = 1701;
  const user = (await rpc.read("res.users", [2], ["name", "van_sale_location_id"]))[0];
  const pick = (await rpc.searchRead("stock.picking", [["name", "=", "M-WH/OUT/03817"]], ["id", "name", "state", "origin", "location_id", "move_ids", "move_line_ids"], { limit: 1 }))[0];
  const moves = await rpc.read("stock.move", pick.move_ids, ["id", "name", "location_id", "location_dest_id", "product_uom_qty", "quantity", "state"]);
  const lines = pick.move_line_ids.length ? await rpc.read("stock.move.line", pick.move_line_ids, ["id", "location_id", "location_dest_id", "quantity", "lot_id"]) : [];
  const expectedLocId = pick.location_id[0];
  const movesOk = moves.every((move) => move.location_id && move.location_id[0] === expectedLocId);
  const linesOk = lines.every((line) => line.location_id && line.location_id[0] === expectedLocId);
  const userShot = await screenshotRecord(page, "res.users", 2, "1701_user_van_location");
  const pickShot = await screenshotRecord(page, "stock.picking", pick.id, "1701_van_delivery");
  await postTask(
    rpc,
    taskId,
    "UAT 1701 - Van Sales source location on delivery order and operation lines",
    user.van_sale_location_id && movesOk && linesOk ? "PASS" : "FAIL",
    [
      "ตรวจ User Administrator ว่ามี Van Sales Source Location",
      "เปิด Delivery Order M-WH/OUT/03817",
      "ตรวจ Source Location บน header, stock.move และ stock.move.line",
      "ยืนยันว่า operation line ใช้ source location ตาม header ไม่กลับไป M-WH/Stock",
    ],
    [
      "User ต้องมี location รถที่กำหนด",
      "DO header ต้องใช้ source location รถ",
      "Move และ detailed operation lines ต้องใช้ source location เดียวกัน",
    ],
    [
      `User ${user.name}: van_sale_location=${m2oName(user.van_sale_location_id)}`,
      `Picking ${pick.name}: source=${m2oName(pick.location_id)}, state=${pick.state}, origin=${pick.origin}`,
      `Move source check=${movesOk}, move_line source check=${linesOk}, move_count=${moves.length}, move_line_count=${lines.length}`,
    ],
    [userShot, pickShot]
  );
  return { user, pick, movesOk, linesOk };
}

async function test1673(rpc, page) {
  const taskId = 1673;
  const so = (await rpc.searchRead("sale.order", [["name", "=", "SOE-260070"]], ["id", "name", "commitment_date", "order_line"], { limit: 1 }))[0];
  const mo = (await rpc.searchRead("mrp.production", [["name", "=", "GMP/MOPH/00534"]], ["id", "name", "date_start", "date_deadline", "source_sale_order_id", "product_id", "state"], { limit: 1 }))[0];
  const product = (await rpc.read("product.product", [mo.product_id[0]], ["display_name", "mfg_lead_time"]))[0];
  const start = new Date(`${mo.date_start.replace(" ", "T")}Z`);
  const deadline = new Date(`${mo.date_deadline.replace(" ", "T")}Z`);
  const diffDays = Math.round((deadline - start) / 86400000);
  const soShot = await screenshotRecord(page, "sale.order", so.id, "1673_so");
  const moShot = await screenshotRecord(page, "mrp.production", mo.id, "1673_mo");
  await postTask(
    rpc,
    taskId,
    "UAT 1673 - MFG Lead Time drives MO Schedule Date",
    diffDays === Number(product.mfg_lead_time || 0) ? "PASS" : "FAIL",
    [
      "เปิด SOE-260070 และ MO GMP/MOPH/00534 ที่ auto-created จาก SO",
      "อ่าน product MFG Lead Time",
      "เทียบ MO date_start กับ MO date_deadline",
      "ตรวจว่า date_start = deadline - MFG Lead Time",
    ],
    [
      "MO Schedule Date ต้องไม่เท่ากับ SO Delivery Date ถ้า product มี MFG Lead Time",
      "สำหรับ product นี้ lead time 5 วัน ต้องทำให้ MO เริ่มก่อน deadline 5 วัน",
    ],
    [
      `SO ${so.name}: commitment_date=${so.commitment_date}`,
      `MO ${mo.name}: date_start=${mo.date_start}, date_deadline=${mo.date_deadline}`,
      `Product ${product.display_name}: mfg_lead_time=${product.mfg_lead_time}, calculated_diff_days=${diffDays}`,
    ],
    [soShot, moShot]
  );
  return { so, mo, product, diffDays };
}

async function createManualMergeScenario(rpc) {
  const stamp = RUN_ID;
  const group1 = await rpc.create("procurement.group", { name: `${stamp} MO Cancel One` });
  const group2 = await rpc.create("procurement.group", { name: `${stamp} MO Cancel Two` });
  const moVals = (groupId, suffix) => ({
    product_id: 8298,
    product_qty: 30000.0,
    product_uom_id: 1,
    bom_id: 2952,
    procurement_group_id: groupId,
    origin: `${stamp} ${suffix}`,
    date_start: "2026-07-20 08:00:00",
  });
  const mo1 = await rpc.create("mrp.production", moVals(group1, "1689-A"), { skip_auto_merge: true });
  const mo2 = await rpc.create("mrp.production", moVals(group2, "1689-B"), { skip_auto_merge: true });
  await rpc.button("mrp.production", "action_confirm", [mo1, mo2]);
  const moData = await rpc.read("mrp.production", [mo1, mo2], ["name", "move_raw_ids"]);
  const rawMoves = await rpc.read("stock.move", moData.flatMap((m) => m.move_raw_ids), ["id", "product_id", "product_uom", "product_uom_qty", "raw_material_production_id"]);
  const raw1 = rawMoves.find((move) => move.raw_material_production_id[0] === mo1 && move.product_id[0] === 8343);
  const raw2 = rawMoves.find((move) => move.raw_material_production_id[0] === mo2 && move.product_id[0] === 8343);
  if (!raw1 || !raw2) throw new Error("Cannot find target raw component 8343 on created MOs");
  async function createPicking(raw, idx, moName) {
    const pickingId = await rpc.create("stock.picking", {
      origin: moName,
      picking_type_id: 57,
      location_id: 22,
      location_dest_id: 176,
      manufacturing_type: "plastic",
      production_ids: [[6, 0, [idx === 1 ? mo1 : mo2]]],
    });
    const moveId = await rpc.create("stock.move", {
      name: `${stamp} transfer component ${idx}`,
      product_id: 8343,
      product_uom_qty: raw.product_uom_qty,
      product_uom: raw.product_uom[0],
      location_id: 22,
      location_dest_id: 176,
      picking_id: pickingId,
      company_id: 1,
      move_dest_ids: [[4, raw.id]],
    });
    await rpc.button("stock.picking", "action_confirm", [pickingId]);
    await rpc.write("stock.move", [moveId], { quantity: raw.product_uom_qty });
    return pickingId;
  }
  const p1 = await createPicking(raw1, 1, moData[0].name);
  const p2 = await createPicking(raw2, 2, moData[1].name);
  const wizardId = await rpc.create("stock.picking.manual.merge.wizard", { picking_ids: [[6, 0, [p1, p2]]] });
  const action = await rpc.button("stock.picking.manual.merge.wizard", "action_merge", [wizardId]);
  const targetId = action.res_id;
  const afterMerge = (await rpc.read("stock.picking", [targetId], ["name", "state", "origin", "move_ids", "production_ids"]))[0];
  const transferMovesAfterMerge = await rpc.read("stock.move", afterMerge.move_ids, ["id", "product_id", "product_uom_qty", "quantity", "state", "move_dest_ids"]);
  await rpc.button("mrp.production", "action_cancel", [mo1]);
  const afterCancelFirst = (await rpc.read("stock.picking", [targetId], ["name", "state", "move_ids", "production_ids"]))[0];
  const transferMovesAfterCancelFirst = await rpc.read("stock.move", afterCancelFirst.move_ids, ["id", "product_id", "product_uom_qty", "quantity", "state", "move_dest_ids"]);
  await rpc.button("mrp.production", "action_cancel", [mo2]);
  const afterCancelSecond = (await rpc.read("stock.picking", [targetId], ["name", "state", "move_ids", "production_ids"]))[0];
  const moFinal = await rpc.read("mrp.production", [mo1, mo2], ["name", "state"]);
  return { mo1, mo2, p1, p2, targetId, afterMerge, transferMovesAfterMerge, afterCancelFirst, transferMovesAfterCancelFirst, afterCancelSecond, moFinal };
}

async function test1689And1690(rpc, page) {
  const scenario = await createManualMergeScenario(rpc);
  const transferShot = await screenshotRecord(page, "stock.picking", scenario.targetId, "1689_1690_manual_merge_transfer");
  const moShot = await screenshotRecord(page, "mrp.production", scenario.mo1, "1689_1690_cancelled_mo");
  const mergedQty = sum(scenario.transferMovesAfterMerge, (move) => move.product_uom_qty);
  const remainingQty = sum(scenario.transferMovesAfterCancelFirst.filter((move) => move.state !== "cancel"), (move) => move.product_uom_qty);
  const mergePass = scenario.afterMerge.production_ids.length === 2 && Math.abs(mergedQty - 0.82) < 0.001;
  const cancelPass = scenario.afterCancelFirst.state !== "cancel" && Math.abs(remainingQty - 0.41) < 0.001 && scenario.afterCancelSecond.state === "cancel";
  await postTask(
    rpc,
    1689,
    "UAT 1689 - Manual merge transfer keeps complete RM demand",
    mergePass ? "PASS" : "FAIL",
    [
      "สร้าง MO 2 ใบด้วย product/BOM เดิม ไม่สร้าง product ใหม่",
      "สร้าง Internal Transfer แยกใบละ 1 รายการตาม raw demand ของ MO",
      "Merge Internal Transfers ผ่าน manual merge wizard",
      "ตรวจ merged transfer qty รวมและ production_ids",
    ],
    [
      "Merge ต้องรวม demand จาก MO ทั้ง 2 ใบครบ",
      "Transfer ต้องไม่หักออกตาม reserved quantity จนขาดรายการ",
      "Merged transfer ต้อง link กลับทั้ง 2 MO",
    ],
    [
      `MO created=${scenario.moFinal.map((m) => `${m.name}:${m.state}`).join(", ")}`,
      `Transfer ${scenario.afterMerge.name}: state=${scenario.afterMerge.state}, production_ids=${scenario.afterMerge.production_ids.join(", ")}`,
      `Move qty after merge=${mergedQty}, move_count=${scenario.transferMovesAfterMerge.length}`,
    ],
    [transferShot]
  );
  await postTask(
    rpc,
    1690,
    "UAT 1690 - Cancel one MO keeps shared merged transfer for remaining MO",
    cancelPass ? "PASS" : "FAIL",
    [
      "ใช้ merged transfer จากเคส 1689",
      "Cancel MO ใบแรก",
      "ตรวจว่า merged transfer ยังไม่ถูก cancel ถ้า MO อีกใบยัง active",
      "Cancel MO ใบที่สอง",
      "ตรวจว่า merged transfer ถูก cancel หลังไม่มี MO active เหลือ",
    ],
    [
      "Cancel MO แรกต้องลด qty เฉพาะ demand ของ MO ที่ cancel",
      "Transfer ต้องยัง active สำหรับ MO ที่เหลือ",
      "เมื่อ cancel MO ทั้งหมด transfer จึงค่อย cancel",
    ],
    [
      `After cancel first MO: transfer_state=${scenario.afterCancelFirst.state}, remaining_qty=${remainingQty}`,
      `After cancel second MO: transfer_state=${scenario.afterCancelSecond.state}`,
      `Final MO states=${scenario.moFinal.map((m) => `${m.name}:${m.state}`).join(", ")}`,
    ],
    [transferShot, moShot]
  );
  return scenario;
}

async function test1691(rpc, page) {
  const taskId = 1691;
  const invoice = (await rpc.searchRead("account.move", [["move_type", "=", "out_invoice"], ["state", "=", "posted"], ["invoice_origin", "ilike", "SOB-263"]], ["id", "name", "invoice_origin", "state", "amount_total"], { limit: 1, order: "id desc" }))[0];
  if (!invoice) {
    await postTask(
      rpc,
      taskId,
      "UAT 1691 - Van Sales tax invoice print",
      "BLOCKED",
      ["ค้นหา posted customer invoice ที่มาจาก Van Sales SOB-263*"],
      ["ต้องมี invoice ตัวอย่างเพื่อ render/print ใบกำกับภาษี"],
      ["ไม่พบ posted customer invoice จาก SOB-263* ในข้อมูลปัจจุบัน จึงยังตรวจ layout print 3+1 จุดไม่ได้"],
      []
    );
    return { blocked: true };
  }
  const shot = await screenshotRecord(page, "account.move", invoice.id, "1691_van_invoice");
  await postTask(
    rpc,
    taskId,
    "UAT 1691 - Van Sales invoice source document check",
    "PARTIAL",
    [
      "ค้นหา posted invoice ที่มี invoice_origin เป็น SOB-263*",
      "เปิด invoice form เพื่อตรวจข้อมูลต้นทางก่อน print",
      "แนบ screenshot form เป็น evidence",
    ],
    [
      "ต้องมีเอกสาร invoice จาก Van Sales สำหรับ render report",
      "ต้องตรวจ PDF layout ต่อในรอบที่มี report name/print action ที่ใช้งานจริง",
    ],
    [
      `พบ invoice ${invoice.name}, origin=${invoice.invoice_origin}, total=${invoice.amount_total}`,
      "ยังไม่ได้ยืนยัน layout PDF 3+1 จุดในรอบนี้ เพราะต้องระบุ report action/เมนู print ที่ลูกค้าใช้จริง",
    ],
    [shot]
  );
  return { invoice };
}

async function main() {
  const rpc = new OdooRpc();
  await rpc.login();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
  await page.goto(`${BASE}/web/login?db=${encodeURIComponent(DB)}`, { waitUntil: "domcontentloaded" });
  await page.locator("input[name='login']").fill(USER);
  await page.locator("input[name='password']").fill(PASSWORD);
  await page.locator("button[type='submit']").click();
  await page.waitForURL(/\/web/, { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3000);

  const results = {};
  const tests = [
    ["1703", () => test1703(rpc, page)],
    ["1701", () => test1701(rpc, page)],
    ["1693", () => test1693(rpc, page)],
    ["1691", () => test1691(rpc, page)],
    ["1689_1690", () => test1689And1690(rpc, page)],
    ["1684", () => test1684(rpc, page)],
    ["1673", () => test1673(rpc, page)],
    ["1667", () => test1667(rpc, page)],
    ["1665", () => test1665(rpc, page)],
    ["1622", () => test1622(rpc, page)],
    ["1596", () => test1596(rpc, page)],
  ];

  for (const [name, fn] of tests) {
    try {
      console.log(`START ${name}`);
      results[name] = { ok: true, data: await fn() };
      console.log(`DONE ${name}`);
    } catch (err) {
      results[name] = { ok: false, error: err.message, stack: err.stack };
      console.error(`FAIL ${name}: ${err.message}`);
      const taskId = Number(name.split("_")[0]);
      if (Number.isFinite(taskId)) {
        try {
          await postTask(
            rpc,
            taskId,
            `UAT ${name} - execution error`,
            "FAIL",
            ["Run automated UI/backend UAT"],
            ["Test must complete without RPC/UI error"],
            [err.message],
            []
          );
        } catch (postErr) {
          console.error(`POST FAIL ${name}: ${postErr.message}`);
        }
      }
    }
  }

  await browser.close();
  const resultPath = path.join(OUT_DIR, `${RUN_ID}_results.json`);
  fs.writeFileSync(resultPath, JSON.stringify(results, null, 2), "utf8");
  console.log(JSON.stringify({ run: RUN_ID, resultPath }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

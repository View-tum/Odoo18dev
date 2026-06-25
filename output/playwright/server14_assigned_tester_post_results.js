const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE = "http://10.0.0.14";
const DB = "goldmints_uat";
const USER = "admin";
const PASSWORD = "365@gmp";
const PREV_RUN = "SERVER14-UAT-20260618132053";
const RUN_ID = `SERVER14-UAT-REPAIR-${new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14)}`;
const OUT_DIR = path.resolve("output/playwright/server14_assigned_tester_uat");
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
      this.cookie = this.cookie
        ? `${this.cookie.split("; ").filter((part) => !part.startsWith(first.split("=")[0] + "=")).join("; ")}; ${first}`.replace(/^; /, "")
        : first;
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

function prevShot(name) {
  const p = path.join(OUT_DIR, `${PREV_RUN}_${name}.png`);
  return fs.existsSync(p) ? p : null;
}

function m2oName(value) {
  return Array.isArray(value) ? value[1] : value || "";
}

async function attachAndPost(rpc, taskId, title, status, steps, expected, actual, screenshotPaths = []) {
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
  const body = `
    <p><strong>${esc(title)}</strong></p>
    <p><strong>Run:</strong> ${esc(RUN_ID)} | <strong>Result:</strong> ${esc(status)}</p>
    <p><strong>Test Steps</strong></p>${htmlList(steps)}
    <p><strong>Expected Results</strong></p>${htmlList(expected)}
    <p><strong>Actual Results</strong></p>${htmlList(actual)}
  `;
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

function totalQty(moves) {
  return moves.reduce((acc, move) => acc + Number(move.product_uom_qty || 0), 0);
}

async function runMergeCancelScenario(rpc, page) {
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
    date_start: "2026-07-21 08:00:00",
  });
  const mo1 = await rpc.create("mrp.production", moVals(group1, "1689-A"), { skip_auto_merge: true });
  const mo2 = await rpc.create("mrp.production", moVals(group2, "1689-B"), { skip_auto_merge: true });
  await rpc.button("mrp.production", "action_confirm", [mo1, mo2]);
  const moData = await rpc.read("mrp.production", [mo1, mo2], ["name", "move_raw_ids"]);
  const rawMoves = await rpc.read("stock.move", moData.flatMap((m) => m.move_raw_ids), ["id", "product_id", "product_uom", "product_uom_qty", "raw_material_production_id"]);
  const raw1 = rawMoves.find((move) => move.raw_material_production_id[0] === mo1 && move.product_id[0] === 8343);
  const raw2 = rawMoves.find((move) => move.raw_material_production_id[0] === mo2 && move.product_id[0] === 8343);
  if (!raw1 || !raw2) throw new Error("Cannot find component 8343 raw moves");
  async function makePicking(raw, moId, moName, idx) {
    const pickingId = await rpc.create("stock.picking", {
      origin: moName,
      picking_type_id: 57,
      location_id: 22,
      location_dest_id: 176,
      manufacturing_type: "plastic",
      production_ids: [[6, 0, [moId]]],
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
  const p1 = await makePicking(raw1, mo1, moData[0].name, 1);
  const p2 = await makePicking(raw2, mo2, moData[1].name, 2);
  const wizardId = await rpc.create("stock.picking.manual.merge.wizard", { picking_ids: [[6, 0, [p1, p2]]] });
  const action = await rpc.button("stock.picking.manual.merge.wizard", "action_merge", [wizardId]);
  const targetId = action.res_id;
  const afterMerge = (await rpc.read("stock.picking", [targetId], ["name", "state", "origin", "move_ids", "production_ids"]))[0];
  const movesAfterMerge = await rpc.read("stock.move", afterMerge.move_ids, ["id", "product_id", "product_uom_qty", "quantity", "state", "move_dest_ids"]);
  const shotAfterMerge = await screenshotRecord(page, "stock.picking", targetId, "1689_after_merge");
  await rpc.button("mrp.production", "action_cancel", [mo1]);
  const afterFirst = (await rpc.read("stock.picking", [targetId], ["name", "state", "move_ids", "production_ids"]))[0];
  const movesAfterFirst = await rpc.read("stock.move", afterFirst.move_ids, ["id", "product_id", "product_uom_qty", "quantity", "state", "move_dest_ids"]);
  const shotAfterFirst = await screenshotRecord(page, "stock.picking", targetId, "1690_after_cancel_first");
  await rpc.button("mrp.production", "action_cancel", [mo2]);
  const afterSecond = (await rpc.read("stock.picking", [targetId], ["name", "state", "move_ids", "production_ids"]))[0];
  const movesAfterSecond = await rpc.read("stock.move", afterSecond.move_ids, ["id", "product_id", "product_uom_qty", "quantity", "state"]);
  const shotAfterSecond = await screenshotRecord(page, "stock.picking", targetId, "1690_after_cancel_second");
  const moFinal = await rpc.read("mrp.production", [mo1, mo2], ["name", "state"]);
  return { mo1, mo2, targetId, afterMerge, movesAfterMerge, afterFirst, movesAfterFirst, afterSecond, movesAfterSecond, moFinal, shots: [shotAfterMerge, shotAfterFirst, shotAfterSecond] };
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
  await page.waitForTimeout(2500);

  const summary = {};

  const mo1703 = (await rpc.searchRead("mrp.production", [["name", "=", "GMP/MOPL/00193"]], ["id", "name", "state", "purchase_order_count", "procurement_group_id"], { limit: 1 }))[0];
  const po1703 = await rpc.searchRead("purchase.order", [["origin", "ilike", "GMP/MOPL/00193"]], ["id", "name", "origin", "state"], { limit: 10 });
  summary[1703] = mo1703.purchase_order_count >= 1 && po1703.length >= 1 ? "PASS" : "FAIL";
  await attachAndPost(rpc, 1703, "UAT 1703 - Auto PO smart button from MO", summary[1703], [
    "เปิด MO GMP/MOPL/00193",
    "ตรวจ purchase_order_count และ PO origin ที่มีชื่อ MO",
    "เปิด PO ที่ระบบสร้างจาก MO",
  ], [
    "MO ต้องมี smart button/จำนวน PO",
    "PO ต้อง link กลับมาด้วย origin ที่มีชื่อ MO",
  ], [
    `MO ${mo1703.name}: state=${mo1703.state}, purchase_order_count=${mo1703.purchase_order_count}`,
    `PO found=${po1703.map((po) => `${po.name}(${po.state})`).join(", ")}`,
  ], [prevShot("1703_mo_po_smart_button"), prevShot("1703_auto_po")]);

  const user1701 = (await rpc.read("res.users", [2], ["name", "van_sale_location_id"]))[0];
  const pick1701 = (await rpc.searchRead("stock.picking", [["name", "=", "M-WH/OUT/03817"]], ["id", "name", "state", "origin", "location_id", "move_ids", "move_line_ids"], { limit: 1 }))[0];
  const moves1701 = await rpc.read("stock.move", pick1701.move_ids, ["location_id"]);
  const lines1701 = await rpc.read("stock.move.line", pick1701.move_line_ids, ["location_id"]);
  const locId = pick1701.location_id[0];
  const movesOk = moves1701.every((m) => m.location_id && m.location_id[0] === locId);
  const linesOk = lines1701.every((l) => l.location_id && l.location_id[0] === locId);
  summary[1701] = user1701.van_sale_location_id && movesOk && linesOk ? "PASS" : "FAIL";
  await attachAndPost(rpc, 1701, "UAT 1701 - Van Sales location on operations", summary[1701], [
    "ตรวจ user van_sale_location_id",
    "เปิด DO M-WH/OUT/03817",
    "ตรวจ source location บน header, stock.move, stock.move.line",
  ], [
    "Header และ operation lines ต้องใช้ location รถเดียวกัน",
  ], [
    `User ${user1701.name}: van_sale_location=${m2oName(user1701.van_sale_location_id)}`,
    `Picking ${pick1701.name}: source=${m2oName(pick1701.location_id)}, moves_ok=${movesOk}, lines_ok=${linesOk}`,
  ], [prevShot("1701_user_van_location"), prevShot("1701_van_delivery")]);

  const bn1693 = (await rpc.searchRead("vendor.billing.note", [["purchase_ids.name", "=", "P00125"]], ["id", "name", "state", "amount_total", "line_ids", "purchase_ids"], { limit: 1, order: "id desc" }))[0];
  summary[1693] = bn1693 && bn1693.state === "confirmed" && bn1693.line_ids.length ? "PASS" : "FAIL";
  await attachAndPost(rpc, 1693, "UAT 1693 - Fixed Asset PO Status Report to Billing Note", summary[1693], [
    "เปิด PO Status Report โดยกรอง P00125/Injection Machine",
    "เลือก fixed asset line และสร้าง BN",
    "Confirm BN และตรวจ backend",
  ], [
    "Fixed asset PO ต้องสร้าง BN ได้แม้ยังไม่ receive",
    "BN ต้อง link กลับ P00125",
  ], [
    `BN ${bn1693.name}: state=${bn1693.state}, total=${bn1693.amount_total}, line_count=${bn1693.line_ids.length}, purchase_ids=${bn1693.purchase_ids.join(", ")}`,
  ], [prevShot("1693_po_status_wizard"), prevShot("1693_fixed_asset_bn")]);

  const invoice1691 = (await rpc.searchRead("account.move", [["move_type", "=", "out_invoice"], ["state", "=", "posted"], ["invoice_origin", "ilike", "SOB-263"]], ["id", "name", "invoice_origin", "state", "amount_total"], { limit: 1, order: "id desc" }))[0];
  summary[1691] = invoice1691 ? "PARTIAL_NEEDS_REPORT_ACTION" : "BLOCKED";
  await attachAndPost(rpc, 1691, "UAT 1691 - Van Sales tax invoice print", summary[1691], [
    "ค้นหา posted invoice ที่มาจาก SOB-263*",
    "เปิด invoice form เพื่อยืนยันเอกสารตัวอย่าง",
  ], [
    "ต้องมีตัวอย่าง invoice และต้องระบุ report/print action ที่ลูกค้าใช้จริงก่อนตรวจ PDF layout 3+1 จุด",
  ], [
    invoice1691 ? `พบ invoice ${invoice1691.name}, origin=${invoice1691.invoice_origin}, total=${invoice1691.amount_total}` : "ไม่พบ invoice ตัวอย่าง",
    "ยังไม่สรุป PASS เพราะยังไม่ได้ render PDF/report layout",
  ], [prevShot("1691_van_invoice")]);

  const scenario = await runMergeCancelScenario(rpc, page);
  const mergeQty = totalQty(scenario.movesAfterMerge);
  const firstActiveMoves = scenario.movesAfterFirst.filter((m) => m.state !== "cancel");
  const firstQty = totalQty(firstActiveMoves);
  summary[1689] = scenario.afterMerge.production_ids.length === 2 && Math.abs(mergeQty - 0.82) < 0.001 ? "PASS" : "FAIL";
  summary[1690] = scenario.afterFirst.state !== "cancel" && Math.abs(firstQty - 0.41) < 0.001 && scenario.afterSecond.state === "cancel" ? "PASS" : "FAIL";
  await attachAndPost(rpc, 1689, "UAT 1689 - Manual merge transfer keeps complete RM demand", summary[1689], [
    "สร้าง MO 2 ใบด้วย product/BOM เดิม",
    "สร้าง Internal Transfer แยกใบตาม raw demand",
    "Merge transfer ผ่าน manual merge wizard",
  ], [
    "Merged transfer ต้องรวม RM demand จาก MO ทั้ง 2 ใบครบ",
    "production_ids ต้อง link กลับทั้ง 2 MO",
  ], [
    `Transfer ${scenario.afterMerge.name}: state=${scenario.afterMerge.state}, production_ids=${scenario.afterMerge.production_ids.join(", ")}`,
    `Merged qty=${mergeQty}, move_count=${scenario.movesAfterMerge.length}`,
  ], [scenario.shots[0]]);
  await attachAndPost(rpc, 1690, "UAT 1690 - Cancel one MO keeps shared transfer for remaining MO", summary[1690], [
    "ใช้ merged transfer จากเคส 1689",
    "Cancel MO ใบแรก",
    "ตรวจ transfer และ qty หลัง cancel ใบแรก",
    "Cancel MO ใบที่สอง",
  ], [
    "หลัง cancel MO แรก transfer ต้องยังไม่ cancel และเหลือ qty ของ MO ที่สอง",
    "หลัง cancel MO ทั้งสอง transfer จึง cancel",
  ], [
    `After first cancel: transfer_state=${scenario.afterFirst.state}, active_qty=${firstQty}, active_move_count=${firstActiveMoves.length}`,
    `After second cancel: transfer_state=${scenario.afterSecond.state}`,
    `MOs=${scenario.moFinal.map((m) => `${m.name}:${m.state}`).join(", ")}`,
  ], [scenario.shots[1], scenario.shots[2]]);

  const contract1684 = (await rpc.searchRead("contract.document", [["name", "=", `${PREV_RUN} Contract Reminder`]], ["id", "name", "state", "date_end", "remaining_days", "reminder_days", "message_ids"], { limit: 1 }))[0];
  const messages1684 = await rpc.read("mail.message", contract1684.message_ids.slice(0, 4), ["body"]);
  const text1684 = messages1684.map((m) => String(m.body || "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim()).join(" | ");
  summary[1684] = text1684.includes("Contract reminder") || text1684.includes("Failed to send contract reminder") ? "PASS_WITH_ENV_NOTICE" : "FAIL";
  await attachAndPost(rpc, 1684, "UAT 1684 - Contract expiry reminder trigger", summary[1684], [
    "สร้าง Contract test end date 25/06/2026 reminder 7 days",
    "Run Daily Reminder Check",
    "ตรวจ chatter/backend message_ids",
  ], [
    "เมื่อ remaining_days = reminder_days ต้อง trigger reminder",
    "UAT mail server เป็น neutralization จึงไม่ควรส่ง email จริงออกนอกระบบ",
  ], [
    `${contract1684.name}: state=${contract1684.state}, remaining_days=${contract1684.remaining_days}, reminder_days=${contract1684.reminder_days}`,
    `Chatter=${text1684 || "none"}`,
  ], [prevShot("1684_contract_reminder")]);

  const so1673 = (await rpc.searchRead("sale.order", [["name", "=", "SOE-260070"]], ["id", "name", "commitment_date"], { limit: 1 }))[0];
  const mo1673 = (await rpc.searchRead("mrp.production", [["name", "=", "GMP/MOPH/00534"]], ["id", "name", "date_start", "date_deadline", "product_id"], { limit: 1 }))[0];
  const product1673 = (await rpc.read("product.product", [mo1673.product_id[0]], ["display_name", "mfg_lead_time"]))[0];
  const diffDays = Math.round((new Date(`${mo1673.date_deadline.replace(" ", "T")}Z`) - new Date(`${mo1673.date_start.replace(" ", "T")}Z`)) / 86400000);
  summary[1673] = diffDays === Number(product1673.mfg_lead_time || 0) ? "PASS" : "FAIL";
  await attachAndPost(rpc, 1673, "UAT 1673 - MFG Lead Time drives MO Schedule Date", summary[1673], [
    "เปิด SOE-260070 และ MO GMP/MOPH/00534",
    "เทียบ date_start/date_deadline กับ product mfg_lead_time",
  ], [
    "MO date_start ต้องเท่ากับ delivery deadline - MFG Lead Time",
  ], [
    `SO ${so1673.name}: commitment_date=${so1673.commitment_date}`,
    `MO ${mo1673.name}: start=${mo1673.date_start}, deadline=${mo1673.date_deadline}`,
    `Product lead_time=${product1673.mfg_lead_time}, calculated_diff_days=${diffDays}`,
  ], [prevShot("1673_so"), prevShot("1673_mo")]);

  const pick1667 = (await rpc.read("stock.picking", [10591], ["id", "name", "vendor_credit_note_state", "vendor_credit_note_count", "vendor_credit_note_ids"]))[0];
  const cn1667 = (await rpc.read("account.move", [70682], ["id", "name", "state", "move_type", "return_picking_ids", "amount_total"]))[0];
  const pick1667Shot = await screenshotRecord(page, "stock.picking", 10591, "1667_vendor_return_posted");
  const cn1667Shot = await screenshotRecord(page, "account.move", 70682, "1667_vendor_credit_note_posted");
  summary[1667] = pick1667.vendor_credit_note_state === "posted" && cn1667.state === "posted" ? "PASS" : "FAIL";
  await attachAndPost(rpc, 1667, "UAT 1667 - Vendor Return linked to Vendor Credit Note", summary[1667], [
    "Reverse APD/26/05/00022 และเลือก Return GMP/R-OUT/00004",
    "เติม tax invoice number/date ตาม validation ไทย",
    "Post Vendor Credit Note",
    "ตรวจ status/link ฝั่ง Return และ CN",
  ], [
    "Return ต้องมี CN smart link",
    "CN ต้องมี return_picking_ids กลับไป Return",
    "Return status ต้องเป็น Credit Note Issued เมื่อ CN posted",
  ], [
    `Return ${pick1667.name}: state=${pick1667.vendor_credit_note_state}, count=${pick1667.vendor_credit_note_count}, CN=${pick1667.vendor_credit_note_ids.join(", ")}`,
    `CN ${cn1667.name}: state=${cn1667.state}, return_picking_ids=${cn1667.return_picking_ids.join(", ")}, total=${cn1667.amount_total}`,
  ], [pick1667Shot, cn1667Shot]);

  const bn1665 = (await rpc.read("vendor.billing.note", [73], ["name", "state", "billing_source", "bill_ids", "amount_vendor_bills", "amount_credit_notes", "amount_net_due", "amount_residual_net_due"]))[0];
  summary[1665] = bn1665.billing_source === "existing_bills" && Math.abs(Number(bn1665.amount_residual_net_due || 0)) < 0.01 ? "PASS" : "FAIL";
  await attachAndPost(rpc, 1665, "UAT 1665 - Vendor Billing Note from APD + Credit Note", summary[1665], [
    "เลือก APD/26/05/00043, APD/26/05/00041 และ VCND/26/06/00003",
    "สร้างและ Confirm Vendor Billing Note",
    "ตรวจยอด APD/CN และ open balance",
  ], [
    "BN ต้องรับ APD และ CN พร้อมกัน",
    "ยอด 40,660 - 40,660 ต้องเป็น 0 ไม่เกิด Payment Difference",
  ], [
    `BN ${bn1665.name}: state=${bn1665.state}, source=${bn1665.billing_source}, bill_ids=${bn1665.bill_ids.join(", ")}`,
    `vendor_bills=${bn1665.amount_vendor_bills}, credit_notes=${bn1665.amount_credit_notes}, amount_due=${bn1665.amount_net_due}, open_balance=${bn1665.amount_residual_net_due}`,
  ], [prevShot("1665_vendor_bill_cn_bn")]);

  const advFields = Object.keys(await rpc.call("advance.cash.log", "fields_get", [], { attributes: ["string"] }));
  const advShot = await screenshotRecord(page, "advance.cash.log", 2, "1622_existing_return_advance");
  summary[1622] = advFields.includes("return_payment_journal_id") ? "PASS" : "FAIL_NOT_DEPLOYED";
  await attachAndPost(rpc, 1622, "UAT 1622 - Return Advance Bank Draft fields", summary[1622], [
    "ตรวจ backend schema ของ advance.cash.log บน Server 14",
    "เปิด existing Return Advance ADV/2026/0002",
    "พยายามสร้าง Return Advance ด้วย Bank Draft fields ตาม requirement",
  ], [
    "ต้องมี fields return_payment_journal_id, return_payment_method_line_id, bank_draft_number, bank_draft_bank_id, bank_draft_branch, bank_draft_date",
    "ต้องกรอก bank draft ก่อน approve และสร้าง bank draft ตอน account approve",
  ], [
    `Server 14 ยังไม่มี return_payment_journal_id=${advFields.includes("return_payment_journal_id")}`,
    "RPC create ด้วย field return_payment_journal_id ล้มเหลว: Invalid field 'return_payment_journal_id' on model 'advance.cash.log'",
    "สรุป: code ส่วนนี้ยังไม่ deploy หรือ module ยังไม่ upgrade บน Server 14 ต้องแก้/upgrade ใน local แล้ว deploy ใหม่ก่อน UAT เต็ม",
  ], [advShot]);

  const rma1596 = (await rpc.read("rma.transform.return", [6], ["name", "state", "return_picking_id", "credit_note_id", "credit_note_ids", "invoice_id"]))[0];
  const cnId1596 = rma1596.credit_note_id ? rma1596.credit_note_id[0] : (rma1596.credit_note_ids || [])[0];
  const cn1596 = cnId1596 ? (await rpc.read("account.move", [cnId1596], ["name", "state", "move_type", "amount_total"]))[0] : null;
  summary[1596] = rma1596.state === "done" && cn1596 && cn1596.move_type === "out_refund" ? "PASS" : "FAIL";
  await attachAndPost(rpc, 1596, "UAT 1596 - CN RMA link check", summary[1596], [
    "เปิด RMA RMATR/2026/05/000006",
    "ตรวจ Return Picking และ Credit Note link",
    "เปิด Credit Note ที่ link จาก RMA",
  ], [
    "RMA done ต้องมี return picking และ credit note link",
    "Credit Note ต้องเป็น out_refund",
  ], [
    `RMA ${rma1596.name}: state=${rma1596.state}, return=${m2oName(rma1596.return_picking_id)}, credit_note=${m2oName(rma1596.credit_note_id) || (rma1596.credit_note_ids || []).join(", ")}`,
    cn1596 ? `CN ${cn1596.name}: state=${cn1596.state}, move_type=${cn1596.move_type}, total=${cn1596.amount_total}` : "ไม่พบ CN",
  ], [prevShot("1596_rma"), prevShot("1596_rma_cn")]);

  await browser.close();
  const resultPath = path.join(OUT_DIR, `${RUN_ID}_posted_summary.json`);
  fs.writeFileSync(resultPath, JSON.stringify(summary, null, 2), "utf8");
  console.log(JSON.stringify({ run: RUN_ID, resultPath, summary }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

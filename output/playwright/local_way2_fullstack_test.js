const fs = require("fs");
const path = require("path");
const { chromium, request } = require("playwright");

const BASE_URL = process.env.ODOO_BASE_URL || "http://127.0.0.1:8811";
const DB = "GoldMints_Uat_Manu";
const LOGIN = "admin";
const PASSWORD = "admin";
const OUT_DIR = path.resolve(__dirname);
const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const runId = `LOCAL-WAY2-${stamp}`;
const resultPath = path.join(OUT_DIR, `local_way2_fullstack_result_${stamp}.json`);
const chatPath = path.join(OUT_DIR, `local_way2_fullstack_chat_${stamp}.txt`);

const result = {
  runId,
  startedAt: new Date().toISOString(),
  backend: {},
  frontend: {},
  chatter: [],
  screenshots: [],
  assertions: [],
};

function writeArtifacts() {
  fs.writeFileSync(resultPath, JSON.stringify(result, null, 2), "utf8");
  fs.writeFileSync(
    chatPath,
    result.chatter.map((entry) => `[${entry.at}] ${entry.target}: ${entry.body}`).join("\n"),
    "utf8"
  );
}

function assertCheck(name, condition, details = {}) {
  const item = { name, pass: Boolean(condition), details };
  result.assertions.push(item);
  if (!condition) {
    writeArtifacts();
    throw new Error(`Assertion failed: ${name} ${JSON.stringify(details)}`);
  }
}

async function rpc(session, model, method, args = [], kwargs = {}) {
  const response = await session.fetch(`${BASE_URL}/web/dataset/call_kw/${model}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    data: {
      jsonrpc: "2.0",
      method: "call",
      params: { model, method, args, kwargs },
    },
  });
  const payload = await response.json();
  if (payload.error) {
    throw new Error(`${model}.${method}: ${JSON.stringify(payload.error)}`);
  }
  return payload.result;
}

async function login(session) {
  const response = await session.fetch(`${BASE_URL}/web/session/authenticate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    data: {
      jsonrpc: "2.0",
      method: "call",
      params: { db: DB, login: LOGIN, password: PASSWORD },
    },
  });
  const payload = await response.json();
  if (!payload.result || !payload.result.uid) {
    throw new Error(`Login failed: ${JSON.stringify(payload)}`);
  }
  result.backend.uid = payload.result.uid;
}

async function searchRead(session, model, domain, fields, limit = 1) {
  return rpc(session, model, "search_read", [domain], { fields, limit });
}

async function readOne(session, model, id, fields) {
  const rows = await rpc(session, model, "read", [[id], fields], {});
  return rows[0];
}

async function postLog(session, model, id, target, body) {
  const fullBody = `[${runId}] ${body}`;
  await rpc(session, model, "message_post", [[id]], {
    body: fullBody,
    message_type: "comment",
    subtype_xmlid: "mail.mt_note",
  });
  result.chatter.push({ at: new Date().toISOString(), target, body: fullBody });
}

async function createScenario(session) {
  const productRows = await searchRead(
    session,
    "product.product",
    [["id", "=", 8298]],
    ["id", "display_name", "uom_id", "product_tmpl_id"],
    1
  );
  const bomRows = await searchRead(
    session,
    "mrp.bom",
    [["id", "=", 2952]],
    ["id", "display_name", "product_tmpl_id", "product_id", "product_uom_id"],
    1
  );
  const manufacturingTypes = await searchRead(
    session,
    "stock.picking.type",
    [
      ["code", "=", "mrp_operation"],
      ["name", "=", "Manufacturing Plastic"],
    ],
    ["id", "display_name"],
    1
  );
  const transferTypes = await searchRead(
    session,
    "stock.picking.type",
    [
      ["code", "=", "internal"],
      ["name", "=", "Transfer Plastic"],
    ],
    ["id", "display_name", "default_location_src_id", "default_location_dest_id"],
    1
  );

  assertCheck("existing product is available", productRows.length === 1, { productId: 8298 });
  assertCheck("existing BOM is available", bomRows.length === 1, { bomId: 2952 });
  assertCheck("Manufacturing Plastic operation exists", manufacturingTypes.length === 1, {});
  assertCheck("Transfer Plastic operation exists", transferTypes.length === 1, {});

  const product = productRows[0];
  const bom = bomRows[0];
  const mrpType = manufacturingTypes[0];
  const transferType = transferTypes[0];
  const sourceLocationId = transferType.default_location_src_id[0];
  const destLocationId = transferType.default_location_dest_id[0];
  const uomId = product.uom_id[0];

  const groupOne = await rpc(session, "procurement.group", "create", [{ name: `${runId} MO 1` }]);
  const groupTwo = await rpc(session, "procurement.group", "create", [{ name: `${runId} MO 2` }]);
  const moBase = {
    product_id: product.id,
    product_qty: 1.0,
    product_uom_id: uomId,
    bom_id: bom.id,
    picking_type_id: mrpType.id,
  };
  const firstMoId = await rpc(
    session,
    "mrp.production",
    "create",
    [{ ...moBase, procurement_group_id: groupOne }],
    { context: { skip_auto_merge: true } }
  );
  const secondMoId = await rpc(
    session,
    "mrp.production",
    "create",
    [{ ...moBase, procurement_group_id: groupTwo }],
    { context: { skip_auto_merge: true } }
  );
  await rpc(session, "mrp.production", "action_confirm", [[firstMoId, secondMoId]], {
    context: { skip_mold_check: true },
  });

  const firstMo = await readOne(session, "mrp.production", firstMoId, ["name", "state", "move_raw_ids"]);
  const secondMo = await readOne(session, "mrp.production", secondMoId, ["name", "state", "move_raw_ids"]);
  assertCheck("both MOs confirmed", firstMo.state === "confirmed" && secondMo.state === "confirmed", {
    firstMo,
    secondMo,
  });
  assertCheck("first MO has raw move", firstMo.move_raw_ids.length > 0, { firstMo: firstMo.name });
  assertCheck("second MO has raw move", secondMo.move_raw_ids.length > 0, { secondMo: secondMo.name });

  const rawOne = await readOne(session, "stock.move", firstMo.move_raw_ids[0], [
    "product_id",
    "product_uom",
    "product_uom_qty",
  ]);
  const rawTwo = await readOne(session, "stock.move", secondMo.move_raw_ids[0], [
    "product_id",
    "product_uom",
    "product_uom_qty",
  ]);

  const createPicking = async (mo, raw, index) => {
    const pickingId = await rpc(session, "stock.picking", "create", [
      {
        picking_type_id: transferType.id,
        location_id: sourceLocationId,
        location_dest_id: destLocationId,
        origin: mo.name,
        manufacturing_type: "plastic",
      },
    ]);
    const moveId = await rpc(session, "stock.move", "create", [
      {
        name: `${runId} RM Transfer ${index}`,
        product_id: raw.product_id[0],
        product_uom_qty: raw.product_uom_qty,
        product_uom: raw.product_uom[0],
        location_id: sourceLocationId,
        location_dest_id: destLocationId,
        picking_id: pickingId,
        move_dest_ids: [[4, mo.move_raw_ids[0]]],
      },
    ]);
    await rpc(session, "stock.picking", "action_confirm", [[pickingId]]);
    return { pickingId, moveId };
  };

  const firstPicking = await createPicking(firstMo, rawOne, 1);
  const secondPicking = await createPicking(secondMo, rawTwo, 2);

  await postLog(session, "mrp.production", firstMoId, firstMo.name, "Created first MO for local fullstack merge/cancel test.");
  await postLog(session, "mrp.production", secondMoId, secondMo.name, "Created second MO for local fullstack merge/cancel test.");
  await postLog(session, "stock.picking", firstPicking.pickingId, "First Transfer", "Created first internal transfer before merge.");
  await postLog(session, "stock.picking", secondPicking.pickingId, "Second Transfer", "Created second internal transfer before merge.");

  const wizardId = await rpc(session, "stock.picking.manual.merge.wizard", "create", [
    { picking_ids: [[6, 0, [firstPicking.pickingId, secondPicking.pickingId]]] },
  ]);
  const action = await rpc(session, "stock.picking.manual.merge.wizard", "action_merge", [[wizardId]]);
  const targetPickingId = action.res_id;
  const targetAfterMerge = await readOne(session, "stock.picking", targetPickingId, [
    "name",
    "state",
    "origin",
    "move_ids",
    "production_ids",
  ]);
  const sourceAfterMerge = await readOne(session, "stock.picking", secondPicking.pickingId, ["name", "state"]);
  const targetMoveAfterMerge = await readOne(session, "stock.move", targetAfterMerge.move_ids[0], [
    "product_uom_qty",
    "state",
    "move_lines_count",
    "move_dest_ids",
  ]);
  const mergedQty = Number(targetMoveAfterMerge.product_uom_qty);

  assertCheck("merge target is first picking", targetPickingId === firstPicking.pickingId, {
    targetPickingId,
    firstPickingId: firstPicking.pickingId,
  });
  assertCheck("merge consolidated to one stock move", targetAfterMerge.move_ids.length === 1, {
    moveIds: targetAfterMerge.move_ids,
  });
  assertCheck("source transfer cancelled after merge", sourceAfterMerge.state === "cancel", sourceAfterMerge);
  assertCheck("merged transfer linked to both MOs", targetAfterMerge.production_ids.length === 2, {
    productionIds: targetAfterMerge.production_ids,
  });
  assertCheck("merged qty equals raw demand sum", Math.abs(mergedQty - rawOne.product_uom_qty - rawTwo.product_uom_qty) < 0.00001, {
    mergedQty,
    rawOneQty: rawOne.product_uom_qty,
    rawTwoQty: rawTwo.product_uom_qty,
  });
  await postLog(
    session,
    "stock.picking",
    targetPickingId,
    targetAfterMerge.name,
    `Merged two transfers into one line. Qty=${mergedQty}. Source ${sourceAfterMerge.name} cancelled.`
  );

  result.backend.created = {
    product: product.display_name,
    bom: bom.display_name,
    firstMo: { id: firstMoId, name: firstMo.name },
    secondMo: { id: secondMoId, name: secondMo.name },
    targetPicking: { id: targetPickingId, name: targetAfterMerge.name },
    cancelledSourcePicking: { id: secondPicking.pickingId, name: sourceAfterMerge.name },
  };

  return {
    firstMoId,
    secondMoId,
    firstMoName: firstMo.name,
    secondMoName: secondMo.name,
    targetPickingId,
    targetPickingName: targetAfterMerge.name,
    rawOneQty: rawOne.product_uom_qty,
    rawTwoQty: rawTwo.product_uom_qty,
    mergedQty,
  };
}

async function frontendVerifyAndCancel(session, scenario) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 950 } });
  const page = await context.newPage();

  await page.goto(`${BASE_URL}/web/login?db=${encodeURIComponent(DB)}`, { waitUntil: "domcontentloaded" });
  if (await page.locator("input[name='login']").count()) {
    await page.fill("input[name='login']", LOGIN);
    await page.fill("input[name='password']", PASSWORD);
    await page.click("button[type='submit']");
  }
  await page.waitForTimeout(1500);

  await page.goto(`${BASE_URL}/web#id=${scenario.targetPickingId}&model=stock.picking&view_type=form`, {
    waitUntil: "domcontentloaded",
  });
  await page.waitForTimeout(1500);
  await page.getByText(scenario.targetPickingName).first().waitFor({ timeout: 30000 });
  const beforeScreenshot = path.join(OUT_DIR, `local_way2_before_cancel_${stamp}.png`);
  await page.screenshot({ path: beforeScreenshot, fullPage: true });
  result.screenshots.push(beforeScreenshot);
  result.frontend.beforeCancelVisible = true;

  await page.goto(`${BASE_URL}/web#id=${scenario.firstMoId}&model=mrp.production&view_type=form`, {
    waitUntil: "domcontentloaded",
  });
  await page.waitForTimeout(1500);
  await page.getByText(scenario.firstMoName).first().waitFor({ timeout: 30000 });
  const cancelButton = page.getByRole("button", { name: /^Cancel$/ }).first();
  await cancelButton.waitFor({ timeout: 30000 });
  await cancelButton.click();
  const confirmButtons = [
    page.getByRole("button", { name: /^Ok$/ }),
    page.getByRole("button", { name: /^Confirm$/ }),
    page.getByRole("button", { name: /^Yes$/ }),
  ];
  for (const button of confirmButtons) {
    if (await button.count()) {
      try {
        await button.first().click({ timeout: 3000 });
        break;
      } catch (error) {}
    }
  }
  await page.waitForTimeout(1500);

  await page.goto(`${BASE_URL}/web#id=${scenario.targetPickingId}&model=stock.picking&view_type=form`, {
    waitUntil: "domcontentloaded",
  });
  await page.waitForTimeout(1500);
  await page.getByText(scenario.targetPickingName).first().waitFor({ timeout: 30000 });
  const afterFirstCancelScreenshot = path.join(OUT_DIR, `local_way2_after_first_mo_cancel_${stamp}.png`);
  await page.screenshot({ path: afterFirstCancelScreenshot, fullPage: true });
  result.screenshots.push(afterFirstCancelScreenshot);
  result.frontend.afterFirstCancelVisible = true;

  await browser.close();
}

async function verifyAfterFirstCancel(session, scenario) {
  const firstMo = await readOne(session, "mrp.production", scenario.firstMoId, ["name", "state"]);
  const secondMo = await readOne(session, "mrp.production", scenario.secondMoId, ["name", "state"]);
  const picking = await readOne(session, "stock.picking", scenario.targetPickingId, [
    "name",
    "state",
    "move_ids",
    "production_ids",
  ]);
  const activeMoves = [];
  for (const moveId of picking.move_ids) {
    const move = await readOne(session, "stock.move", moveId, ["state", "product_uom_qty", "quantity"]);
    if (move.state !== "cancel") {
      activeMoves.push(move);
    }
  }
  assertCheck("frontend cancel changed first MO to cancel", firstMo.state === "cancel", firstMo);
  assertCheck("second MO remains active after first cancel", secondMo.state !== "cancel", secondMo);
  assertCheck("shared merged transfer remains active after first cancel", picking.state !== "cancel", picking);
  assertCheck("shared merged transfer has one active move after first cancel", activeMoves.length === 1, activeMoves);
  assertCheck(
    "shared merged transfer qty reduced to remaining MO demand",
    Math.abs(Number(activeMoves[0].product_uom_qty) - scenario.rawTwoQty) < 0.00001,
    { activeQty: activeMoves[0].product_uom_qty, expected: scenario.rawTwoQty }
  );
  await postLog(
    session,
    "stock.picking",
    scenario.targetPickingId,
    scenario.targetPickingName,
    `After cancelling ${scenario.firstMoName} from UI, transfer stayed active and qty reduced to ${activeMoves[0].product_uom_qty}.`
  );
}

async function verifySecondCancelBackend(session, scenario) {
  await rpc(session, "mrp.production", "action_cancel", [[scenario.secondMoId]]);
  const secondMo = await readOne(session, "mrp.production", scenario.secondMoId, ["name", "state"]);
  const picking = await readOne(session, "stock.picking", scenario.targetPickingId, ["name", "state"]);
  assertCheck("backend cancel changed second MO to cancel", secondMo.state === "cancel", secondMo);
  assertCheck("merged transfer cancels when no active MO remains", picking.state === "cancel", picking);
  await postLog(
    session,
    "stock.picking",
    scenario.targetPickingId,
    scenario.targetPickingName,
    `After cancelling ${scenario.secondMoName}, no active MO remained and transfer moved to ${picking.state}.`
  );
}

(async () => {
  const session = await request.newContext({ baseURL: BASE_URL });
  try {
    await login(session);
    const scenario = await createScenario(session);
    await frontendVerifyAndCancel(session, scenario);
    await verifyAfterFirstCancel(session, scenario);
    await verifySecondCancelBackend(session, scenario);
    result.finishedAt = new Date().toISOString();
    result.status = "passed";
  } catch (error) {
    result.finishedAt = new Date().toISOString();
    result.status = "failed";
    result.error = error.stack || String(error);
    throw error;
  } finally {
    writeArtifacts();
    await session.dispose();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});

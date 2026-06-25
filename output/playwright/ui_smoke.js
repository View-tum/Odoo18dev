const { chromium } = require('playwright');
const fs = require('fs');

const base = 'http://127.0.0.1:8811';
const outDir = 'output/playwright';
const results = [];

function failText(text) {
  return /RPC_ERROR|Odoo Server Error|Traceback|Internal Server Error/i.test(text || '');
}

async function login(page) {
  await page.goto(`${base}/web/login`, { waitUntil: 'domcontentloaded' });
  const dbInput = page.locator('input[name="db"]');
  if (await dbInput.count()) {
    await dbInput.fill('GoldMints_Uat_Manu');
  }
  await page.locator('input[name="login"]').fill('admin');
  await page.locator('input[name="password"]').fill('admin');
  await Promise.all([
    page.waitForLoadState('networkidle', { timeout: 60000 }).catch(() => {}),
    page.locator('button[type="submit"], input[type="submit"]').first().click(),
  ]);
  await page.waitForSelector('.o_web_client, input[name="login"]', { timeout: 60000 });
  if (await page.locator('input[name="login"]').count()) {
    throw new Error('Login form still visible after submit');
  }
}

async function getActionId(page, xmlid) {
  const result = await page.evaluate(async (xmlid) => {
    const res = await fetch('/web/dataset/call_kw/ir.model.data/xmlid_to_res_model_res_id', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'call',
        params: {
          model: 'ir.model.data',
          method: 'xmlid_to_res_model_res_id',
          args: [xmlid],
          kwargs: {},
        },
        id: Date.now(),
      }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error.data && data.error.data.message || data.error.message);
    return data.result;
  }, xmlid);
  return Array.isArray(result) ? result[1] : result;
}

async function check(page, name, hash, expectedAny = []) {
  const url = `${base}/web#${hash}`;
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.o_web_client', { timeout: 60000 });
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const text = await page.locator('body').innerText({ timeout: 10000 });
  if (failText(text)) {
    throw new Error(`${name}: page contains server/RPC error`);
  }
  const matched = expectedAny.filter((word) => text.includes(word));
  if (expectedAny.length && !matched.length) {
    throw new Error(`${name}: expected one of ${expectedAny.join(', ')}`);
  }
  const safeName = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  await page.screenshot({ path: `${outDir}/${safeName}.png`, fullPage: true });
  results.push({ name, ok: true, matched, url: page.url() });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 950 } });
  const page = await context.newPage();
  page.on('pageerror', (err) => results.push({ name: 'pageerror', ok: false, error: err.message }));
  page.on('console', (msg) => {
    if (msg.type() === 'error' && !msg.text().includes('Failed to load resource')) {
      results.push({ name: 'console-error', ok: false, error: msg.text() });
    }
  });
  try {
    await login(page);
    results.push({ name: 'login', ok: true, url: page.url() });

    await check(page, 'Vendor Billing Note List', 'action=vendor_billing_note.action_vendor_billing_note', ['Vendor Billing Notes', 'Billing Note', 'Vendor Bills', 'Credit Notes']);
    await check(page, 'PO Status Billing Wizard', 'action=purchase_order_status_report.action_purchase_order_status_report_wizard', ['รายงานสถานะคำสั่งซื้อ', 'สถานะการวางบิล', 'สถานะการตั้งหนี้']);
    await page.getByText('Preview', { exact: true }).click();
    await page.waitForTimeout(8000);
    const poStatusText = await page.locator('body').innerText({ timeout: 10000 });
    if (failText(poStatusText)) {
      throw new Error('PO Status Billing Wizard Preview: page contains server/RPC error');
    }
    for (const expected of ['Lines', 'Select APD/CN', 'Select Billable', 'Vendor Bill', 'Vendor Credit Note', 'Billing Note']) {
      if (!poStatusText.includes(expected)) {
        throw new Error(`PO Status Billing Wizard Preview: missing ${expected}`);
      }
    }
    await page.screenshot({ path: `${outDir}/po-status-billing-wizard-preview.png`, fullPage: true });
    results.push({ name: 'PO Status Billing Wizard Preview', ok: true, matched: ['Lines', 'Select APD/CN', 'Select Billable', 'Vendor Bill', 'Vendor Credit Note', 'Billing Note'], url: page.url() });
    await check(page, 'MRP Production List', 'action=mrp.mrp_production_action', ['Manufacturing Orders', 'Shopfloor', 'Manufacturing Type']);
    await check(page, 'Parallel Shopfloor Client Action', 'action=mrp_parallel_console.mrp_parallel_console_action_root', ['GMP Shop Floor', 'Open Console', 'Plastic Shop Floor']);
  } finally {
    await browser.close();
  }

  fs.writeFileSync(`${outDir}/ui-smoke-results.json`, JSON.stringify(results, null, 2));
  const failed = results.filter((r) => r.ok === false);
  console.log(JSON.stringify(results, null, 2));
  if (failed.length) process.exit(1);
})().catch((err) => {
  fs.writeFileSync(`${outDir}/ui-smoke-error.txt`, err.stack || String(err));
  console.error(err.stack || err.message || err);
  process.exit(1);
});

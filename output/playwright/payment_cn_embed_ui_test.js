const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const baseUrl = process.env.ODOO_URL || 'http://127.0.0.1:8811';
const db = process.env.ODOO_DB || 'GoldMints_Uat_Manu';
const login = process.env.ODOO_LOGIN || 'admin';
const password = process.env.ODOO_PASSWORD || 'admin';
const root = path.resolve(__dirname);
const dataPath = path.join(root, 'payment_cn_embed_ui_data.json');
const resultPath = path.join(root, 'payment_cn_embed_ui_results.json');
const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

function clean(value) {
  return String(value).replace(/[^a-z0-9_-]+/gi, '_').replace(/^_+|_+$/g, '').toLowerCase();
}

async function visible(locator, timeout = 1500) {
  try {
    await locator.first().waitFor({ state: 'visible', timeout });
    return true;
  } catch {
    return false;
  }
}

async function clickFirstVisible(page, locators, timeout = 1500) {
  for (const locator of locators) {
    if (await visible(locator, timeout)) {
      await locator.first().click();
      return true;
    }
  }
  return false;
}

async function loginOdoo(page) {
  await page.goto(`${baseUrl}/web/login?db=${encodeURIComponent(db)}`, { waitUntil: 'domcontentloaded' });
  if (await visible(page.locator('input[name="login"]'), 5000)) {
    await page.locator('input[name="login"]').fill(login);
    await page.locator('input[name="password"]').fill(password);
    await Promise.all([
      page.waitForLoadState('networkidle').catch(() => {}),
      page.getByRole('button', { name: /Log in|เข้าสู่ระบบ/i }).click()
    ]);
  }
  await page.waitForLoadState('networkidle').catch(() => {});
}

async function openMoveList(page, scenario) {
  const actionId = scenario.action_id || 261;
  const domain = encodeURIComponent(JSON.stringify([['id', 'in', scenario.move_ids]]));
  await page.goto(`${baseUrl}/web#action=${actionId}&model=account.move&view_type=list&domain=${domain}`, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.locator('table.o_list_table, .o_list_renderer').first().waitFor({ state: 'visible', timeout: 30000 });
  for (const moveName of scenario.move_names) {
    await page.getByText(moveName, { exact: false }).first().waitFor({ state: 'visible', timeout: 25000 });
  }
}

async function selectDisplayedRows(page, expectedCount) {
  const rows = page.locator('tbody tr.o_data_row');
  await rows.first().waitFor({ state: 'visible', timeout: 30000 });
  const count = await rows.count();
  if (count < expectedCount) {
    throw new Error(`Expected at least ${expectedCount} rows, found ${count}`);
  }
  for (let index = 0; index < expectedCount; index += 1) {
    await rows.nth(index).locator('.o_list_record_selector').click();
  }
}

async function selectScenarioRows(page, scenario) {
  for (const moveName of scenario.move_names) {
    const row = page.locator('tbody tr.o_data_row').filter({ hasText: moveName }).first();
    await row.waitFor({ state: 'visible', timeout: 30000 });
    const selector = row.locator('.o_list_record_selector');
    await selector.click();
  }
}

async function openRegisterPayment(page) {
  const payClicked = await clickFirstVisible(page, [
    page.getByRole('button', { name: /^Pay$/i }),
    page.getByRole('button', { name: /ชำระเงิน|จ่าย/i })
  ], 5000);
  if (payClicked) {
    await page.getByRole('button', { name: /Create Payment|สร้าง.*ชำระ|ชำระเงิน/i }).waitFor({ state: 'visible', timeout: 45000 });
    return;
  }
  const actionOpened = await clickFirstVisible(page, [
    page.getByRole('button', { name: /^Actions$/i }),
    page.getByRole('button', { name: /^Action$/i }),
    page.getByRole('button', { name: /การดำเนินการ/i }),
    page.locator('.o_cp_action_menus button.dropdown-toggle'),
    page.locator('.o_cp_action_menus button')
  ], 3000);
  if (!actionOpened) {
    throw new Error('Pay or Action menu was not visible after selecting rows');
  }
  const registerClicked = await clickFirstVisible(page, [
    page.getByRole('menuitem', { name: /^Register Payment$/i }),
    page.getByRole('menuitem', { name: /Register Payment/i }),
    page.locator('.dropdown-menu .dropdown-item').filter({ hasText: /Register Payment|ลงทะเบียน.*ชำระ|ชำระเงิน/i })
  ], 5000);
  if (!registerClicked) {
    throw new Error('Register Payment menu item was not visible');
  }
  await page.getByRole('button', { name: /Create Payment|สร้าง.*ชำระ|ชำระเงิน/i }).waitFor({ state: 'visible', timeout: 45000 });
}

async function clickCreatePayment(page) {
  const clicked = await clickFirstVisible(page, [
    page.locator('.modal-footer button[name="action_create_payments"]'),
    page.getByRole('button', { name: /^Create Payment$/i }),
    page.getByRole('button', { name: /Create Payment/i }),
    page.getByRole('button', { name: /สร้าง.*ชำระ|ชำระเงิน/i }),
    page.locator('.modal-footer button.btn-primary')
  ], 5000);
  if (!clicked) {
    throw new Error('Create Payment button was not visible');
  }
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(4000);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 950 } });
  const page = await context.newPage();
  const results = {
    baseUrl,
    db,
    prefix: data.prefix,
    startedAt: new Date().toISOString(),
    scenarios: {}
  };

  try {
    await loginOdoo(page);
    const scenarios = {
      customer_cn: { ...data.scenarios.customer_cn, action_id: 262 },
      vendor_cn: { ...data.scenarios.vendor_cn, action_id: 265 },
      normal_invoice: { ...data.scenarios.normal_invoice, action_id: 262 }
    };
    results.skipped = {
      cross_settlement: 'Journal Entries list has no standard Pay button; verified by backend integration tests.'
    };
    for (const [key, scenario] of Object.entries(scenarios)) {
      const name = clean(key);
      const listShot = path.join(root, `payment_cn_${name}_list.png`);
      const wizardShot = path.join(root, `payment_cn_${name}_wizard.png`);
      const afterShot = path.join(root, `payment_cn_${name}_after.png`);
      const errorShot = path.join(root, `payment_cn_${name}_error.png`);
      const entry = {
        moveIds: scenario.move_ids,
        moveNames: scenario.move_names,
        expectedAmount: scenario.expected_amount,
        listScreenshot: listShot,
        wizardScreenshot: wizardShot,
        afterScreenshot: afterShot,
        status: 'started'
      };
      results.scenarios[key] = entry;
      try {
        await openMoveList(page, scenario);
        await page.screenshot({ path: listShot, fullPage: true });
        await selectScenarioRows(page, scenario);
        await openRegisterPayment(page);
        const wizardText = await page.locator('body').innerText({ timeout: 10000 });
        entry.amountVisible = wizardText.includes(scenario.expected_amount.toFixed(2)) || wizardText.includes(scenario.expected_amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        entry.wizardTextSample = wizardText.slice(0, 2000);
        await page.screenshot({ path: wizardShot, fullPage: true });
        await clickCreatePayment(page);
        const afterText = await page.locator('body').innerText({ timeout: 10000 }).catch(() => '');
        entry.afterTextSample = afterText.slice(0, 2000);
        entry.urlAfter = page.url();
        entry.hasRpcError = /RPC_ERROR|Odoo Server Error|Traceback/i.test(afterText);
        entry.status = entry.hasRpcError ? 'failed_rpc_error' : 'clicked';
        await page.screenshot({ path: afterShot, fullPage: true });
      } catch (error) {
        entry.status = 'failed';
        entry.error = String(error && error.stack ? error.stack : error);
        await page.screenshot({ path: errorShot, fullPage: true }).catch(() => {});
        entry.errorScreenshot = errorShot;
      }
      fs.writeFileSync(resultPath, JSON.stringify(results, null, 2));
    }
  } catch (error) {
    results.fatal = String(error && error.stack ? error.stack : error);
    await page.screenshot({ path: path.join(root, 'payment_cn_fatal_error.png'), fullPage: true }).catch(() => {});
  } finally {
    results.finishedAt = new Date().toISOString();
    fs.writeFileSync(resultPath, JSON.stringify(results, null, 2));
    await browser.close();
  }

  const failed = results.fatal || Object.values(results.scenarios).some((scenario) => scenario.status === 'failed' || scenario.status.startsWith('failed_'));
  if (failed) {
    process.exitCode = 1;
  }
})();

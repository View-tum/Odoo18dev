const { chromium } = require('playwright');
(async () => {
  const base = 'http://127.0.0.1:8811';
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  const badResponses = [];
  page.on('response', (r) => { if (r.status() >= 400) badResponses.push({status: r.status(), url: r.url()}); });
  await page.goto(`${base}/web/login`, { waitUntil: 'domcontentloaded' });
  if (await page.locator('input[name="db"]').count()) await page.locator('input[name="db"]').fill('GoldMints_Uat_Manu');
  await page.locator('input[name="login"]').fill('admin');
  await page.locator('input[name="password"]').fill('admin');
  await page.locator('button[type="submit"], input[type="submit"]').first().click();
  await page.waitForSelector('.o_web_client', { timeout: 60000 });
  await page.goto(`${base}/web#action=base_setup.action_general_configuration`, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(8000);
  const search = page.locator('input[placeholder="Search..."], input.o_searchview_input, .o_setting_search input').first();
  if (await search.count()) {
    await search.fill('Mobile Warehouse Invoicing');
    await page.waitForTimeout(5000);
  }
  await page.waitForFunction(() => document.body.innerText.includes('Mobile Warehouse Invoicing'), null, { timeout: 60000 });
  const text = await page.locator('body').innerText();
  if (/RPC_ERROR|Odoo Server Error|Traceback|Internal Server Error/i.test(text)) throw new Error('Settings page contains server/RPC error');
  const expected = ['Mobile Warehouse Invoicing', 'Cash Journal', 'Cheque Journal', 'Bank Transfer Journal', 'Default Auto Difference Account', 'Default Auto Difference Label'];
  const missing = expected.filter((word) => !text.includes(word));
  if (missing.length) throw new Error(`Settings missing: ${missing.join(', ')}`);
  await page.screenshot({ path: 'output/playwright/general-settings-mobile-warehouse-section.png', fullPage: true });
  const relevantBad = badResponses.filter((r) => !r.url.includes('/ui_customization/static/description/icon.png'));
  console.log(JSON.stringify({ ok: true, matched: expected, ignored404: badResponses.length - relevantBad.length, relevantBad }, null, 2));
  if (relevantBad.length) process.exit(1);
  await browser.close();
})();

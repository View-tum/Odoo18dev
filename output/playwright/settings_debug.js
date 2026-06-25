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
  await page.waitForTimeout(8000);
  const text1 = await page.locator('body').innerText();
  const search = page.locator('input[placeholder="Search..."], input.o_searchview_input, .o_setting_search input').first();
  if (await search.count()) {
    await search.fill('Mobile Warehouse Invoicing');
    await page.waitForTimeout(5000);
  }
  const text2 = await page.locator('body').innerText();
  await page.screenshot({ path: 'output/playwright/settings-mobile-debug.png', fullPage: true });
  console.log('URL=' + page.url());
  console.log('BAD=' + JSON.stringify(badResponses.slice(0, 20), null, 2));
  console.log(text2.slice(0, 5000));
  await browser.close();
})();

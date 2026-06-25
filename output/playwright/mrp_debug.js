const { chromium } = require('playwright');
(async () => {
  const base = 'http://127.0.0.1:8811';
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  await page.goto(`${base}/web/login`, { waitUntil: 'domcontentloaded' });
  if (await page.locator('input[name="db"]').count()) await page.locator('input[name="db"]').fill('GoldMints_Uat_Manu');
  await page.locator('input[name="login"]').fill('admin');
  await page.locator('input[name="password"]').fill('admin');
  await page.locator('button[type="submit"], input[type="submit"]').first().click();
  await page.waitForSelector('.o_web_client', { timeout: 60000 });
  await page.goto(`${base}/web#action=mrp.mrp_production_action`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(6000);
  const text = await page.locator('body').innerText();
  await page.screenshot({ path: 'output/playwright/mrp-production-debug.png', fullPage: true });
  console.log('URL=' + page.url());
  console.log(text.slice(0, 4000));
  await browser.close();
})();

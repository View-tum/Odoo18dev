const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const base = 'http://10.0.0.14';
const db = 'goldmints_uat';
const out = path.resolve('scratch/server14_assigned_tester_update/screenshots');
fs.mkdirSync(out, { recursive: true });

(async () => {
  const auth = await fetch(`${base}/web/session/authenticate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'call',
      params: { db, login: 'admin', password: '365@gmp' },
    }),
  });
  const setCookie = auth.headers.get('set-cookie') || '';
  const match = setCookie.match(/session_id=([^;]+)/);
  if (!match) {
    throw new Error('Cannot get Odoo session_id');
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1600, height: 950 },
    deviceScaleFactor: 1,
  });
  await context.addCookies([
    { name: 'session_id', value: match[1], domain: '10.0.0.14', path: '/' },
  ]);
  const page = await context.newPage();
  page.setDefaultTimeout(30000);

  const taskIds = [1684, 1667, 1665, 1622, 1596];
  for (const id of taskIds) {
    await page.goto(`${base}/web?db=${encodeURIComponent(db)}#id=${id}&model=project.task&view_type=form`, {
      waitUntil: 'domcontentloaded',
      timeout: 45000,
    });
    await page.waitForTimeout(7000);
    const tab = page.getByText('Test Step & Expected Result', { exact: true });
    if (await tab.count()) {
      await tab.first().click().catch(() => {});
      await page.waitForTimeout(1500);
    }
    await page.screenshot({
      path: path.join(out, `task_${id}_test_tab.png`),
      fullPage: true,
      timeout: 30000,
    });
    console.log('screenshot', id, page.url());
  }

  await page.goto(`${base}/web?db=${encodeURIComponent(db)}#model=project.task&view_type=list`, {
    waitUntil: 'domcontentloaded',
    timeout: 45000,
  });
  await page.waitForTimeout(7000);
  await page.screenshot({
    path: path.join(out, 'project_task_list_after_update.png'),
    fullPage: true,
    timeout: 30000,
  });
  await browser.close();
})();

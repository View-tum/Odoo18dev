const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const base = 'http://10.0.0.14';
const db = 'goldmints_uat';
const out = path.resolve('scratch/server14_task1596_rma_cn/screenshots');
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
  if (!match) throw new Error('Cannot get Odoo session_id');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1600, height: 950 },
    deviceScaleFactor: 1,
  });
  await context.addCookies([{ name: 'session_id', value: match[1], domain: '10.0.0.14', path: '/' }]);
  const page = await context.newPage();
  page.setDefaultTimeout(30000);

  const pages = [
    {
      name: 'task_1596_thai_test_result.png',
      url: `${base}/web?db=${encodeURIComponent(db)}#id=1596&model=project.task&view_type=form`,
      tab: 'Test Step & Expected Result',
    },
    {
      name: 'rma_0022_form.png',
      url: `${base}/web?db=${encodeURIComponent(db)}#id=22&model=crm.claim.ept&view_type=form`,
    },
    {
      name: 'cn_70245_form.png',
      url: `${base}/web?db=${encodeURIComponent(db)}#id=70245&model=account.move&view_type=form`,
    },
  ];

  for (const item of pages) {
    await page.goto(item.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(7000);
    if (item.tab) {
      const tab = page.getByText(item.tab, { exact: true });
      if (await tab.count()) {
        await tab.first().click().catch(() => {});
        await page.waitForTimeout(1500);
      }
    }
    await page.screenshot({ path: path.join(out, item.name), fullPage: true, timeout: 30000 });
    console.log(item.name, page.url());
  }
  await browser.close();
})();

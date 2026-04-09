const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

async function main() {
  const cfgPath = process.argv[2];
  if (!cfgPath) {
    throw new Error('Usage: node capture_odoo_page.js <config.json>');
  }

  const rawCfg = fs.readFileSync(cfgPath, 'utf8').replace(/^\uFEFF/, '');
  const cfg = JSON.parse(rawCfg);
  const outDir = cfg.output_dir;
  fs.mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });

  const loginUrl = cfg.db
    ? `${cfg.base_url}/web/login?db=${encodeURIComponent(cfg.db)}`
    : `${cfg.base_url}/web/login`;
  await page.goto(loginUrl, { waitUntil: 'domcontentloaded' });
  await page.fill('input[name="login"]', cfg.login);
  await page.fill('input[name="password"]', cfg.password);
  await page.click('button[type="submit"]');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(cfg.post_login_wait_ms || 4000);

  if (cfg.target_url) {
    await page.goto(cfg.target_url, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(cfg.post_nav_wait_ms || 2500);
  }

  if (Array.isArray(cfg.actions)) {
    for (const action of cfg.actions) {
      if (action.type === 'goto') {
        await page.goto(action.url, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(action.wait_ms || cfg.post_nav_wait_ms || 2500);
      } else if (action.type === 'click') {
        await page.click(action.selector);
        await page.waitForLoadState('domcontentloaded');
        await page.waitForTimeout(action.wait_ms || cfg.post_click_wait_ms || 2000);
      } else if (action.type === 'fill') {
        await page.fill(action.selector, action.value || '');
      } else if (action.type === 'select') {
        await page.selectOption(action.selector, action.value);
      } else if (action.type === 'wait') {
        await page.waitForTimeout(action.ms || 1000);
      }
    }
  }

  const screenshotPath = path.join(outDir, cfg.filename || 'page.png');
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const boxes = [];
  if (Array.isArray(cfg.highlight_selectors)) {
    for (const item of cfg.highlight_selectors) {
      const locator = page.locator(item.selector).first();
      const count = await locator.count();
      if (!count) continue;
      const box = await locator.boundingBox();
      if (!box) continue;
      boxes.push({
        label: item.label || '',
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
      });
    }
  }

  const metaPath = path.join(outDir, (cfg.filename || 'page.png') + '.json');
  fs.writeFileSync(metaPath, JSON.stringify({
    screenshot: screenshotPath,
    url: page.url(),
    boxes,
  }, null, 2), 'utf8');

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

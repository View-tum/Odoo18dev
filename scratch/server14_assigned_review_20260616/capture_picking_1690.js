const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const baseUrl = "http://10.0.0.14";
const db = "goldmints_uat";
const login = "admin";
const password = "365@gmp";
const outDir = path.join("scratch", "server14_assigned_review_20260616", "screenshots");
const outPath = path.join(outDir, "task1690_transfer_links_two_mos.png");

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  const authResponse = await page.request.post(`${baseUrl}/web/session/authenticate`, {
    data: {
      jsonrpc: "2.0",
      method: "call",
      params: { db, login, password },
    },
  });
  if (!authResponse.ok()) {
    throw new Error(`Authentication HTTP ${authResponse.status()}`);
  }
  const authPayload = await authResponse.json();
  if (!authPayload.result || !authPayload.result.uid) {
    throw new Error("Authentication failed");
  }
  await page.goto(`${baseUrl}/web?debug=1#id=10868&model=stock.picking&view_type=form`, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForSelector("body", { timeout: 60000 });
  await page.waitForTimeout(8000);
  await page.screenshot({ path: outPath, fullPage: true });
  console.log(outPath);
  await browser.close();
})();

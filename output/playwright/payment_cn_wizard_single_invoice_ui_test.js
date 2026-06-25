const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const baseUrl = process.env.ODOO_URL || 'http://127.0.0.1:8812';
const db = process.env.ODOO_DB || 'GoldMints_Uat_Manu';
const login = process.env.ODOO_LOGIN || 'admin';
const password = process.env.ODOO_PASSWORD || 'admin';
const invoiceId = Number(process.env.INVOICE_ID || 74511);
const invoiceName = process.env.INVOICE_NAME || 'INV-D/2026/00021';
const creditNoteName = process.env.CREDIT_NOTE_NAME || 'RINV-D/2026/00004';
const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const root = __dirname;
const resultPath = path.join(root, 'payment_cn_wizard_single_invoice_ui_result.json');
const logPath = path.join(root, 'payment_cn_wizard_single_invoice_chat_log.txt');

const shots = {
  invoice: path.join(root, 'payment_cn_wizard_single_invoice_01_invoice.png'),
  wizardBefore: path.join(root, 'payment_cn_wizard_single_invoice_02_wizard_before.png'),
  wizardAfter: path.join(root, 'payment_cn_wizard_single_invoice_03_wizard_after_select_cn.png'),
  afterCreate: path.join(root, 'payment_cn_wizard_single_invoice_04_after_create_payment.png'),
  error: path.join(root, 'payment_cn_wizard_single_invoice_error.png'),
};

async function visible(locator, timeout = 3000) {
  try {
    await locator.first().waitFor({ state: 'visible', timeout });
    return true;
  } catch {
    return false;
  }
}

async function clickFirst(page, locators, timeout = 3000) {
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
  if (await visible(page.locator('input[name="login"]'), 10000)) {
    await page.locator('input[name="login"]').fill(login);
    await page.locator('input[name="password"]').fill(password);
    await Promise.all([
      page.waitForLoadState('networkidle').catch(() => {}),
      page.locator('button[type="submit"], input[type="submit"]').first().click(),
    ]);
  }
  await page.waitForLoadState('networkidle').catch(() => {});
}

async function openInvoice(page) {
  await page.goto(`${baseUrl}/web#action=262&id=${invoiceId}&model=account.move&view_type=form`, {
    waitUntil: 'domcontentloaded',
  });
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.getByText(invoiceName, { exact: false }).first().waitFor({ state: 'visible', timeout: 45000 });
}

async function openPaymentWizard(page) {
  const clicked = await clickFirst(page, [
    page.getByRole('button', { name: /^Pay$/i }),
    page.getByRole('button', { name: /Register Payment/i }),
    page.getByRole('button', { name: /ชำระเงิน|ลงทะเบียน.*ชำระ/i }),
    page.locator('button[name="action_register_payment"]'),
  ], 8000);
  if (!clicked) {
    throw new Error('Payment button was not visible on invoice form');
  }
  await page.locator('.modal:visible, .o_dialog:visible').first().waitFor({ state: 'visible', timeout: 45000 });
  await page.getByText(/Credit Notes Applied in This Payment|Create Payment|Register Payment/i).first().waitFor({
    state: 'visible',
    timeout: 45000,
  });
}

async function selectCreditNote(page) {
  const modal = page.locator('.modal:visible, .o_dialog:visible').first();
  await modal.getByText(creditNoteName, { exact: false }).first().waitFor({ state: 'visible', timeout: 45000 });
  const row = modal.locator('tr').filter({ hasText: creditNoteName }).first();
  await row.waitFor({ state: 'visible', timeout: 10000 });
  const checkbox = row.locator('input[type="checkbox"], .form-check-input, .o_field_boolean input, .o_boolean_toggle input, .o_boolean_toggle').first();
  if (!(await visible(checkbox, 5000))) {
    throw new Error(`Checkbox for ${creditNoteName} was not visible`);
  }
  const tagName = await checkbox.evaluate((node) => node.tagName.toLowerCase()).catch(() => '');
  if (tagName === 'input') {
    await checkbox.check({ force: true });
  } else {
    await checkbox.click({ force: true });
  }
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(1500);
}

async function createPayment(page) {
  const clicked = await clickFirst(page, [
    page.locator('.modal-footer button[name="action_create_payments"]'),
    page.locator('.modal-footer button.btn-primary').filter({ hasText: /Create Payment|ชำระ|สร้าง/i }),
    page.getByRole('button', { name: /^Create Payment$/i }),
    page.getByRole('button', { name: /Create Payment|สร้าง.*ชำระ|ชำระ/i }),
  ], 8000);
  if (!clicked) {
    throw new Error('Create Payment button was not visible');
  }
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(3000);
}

(async () => {
  fs.mkdirSync(root, { recursive: true });
  const result = {
    baseUrl,
    db,
    invoiceId,
    invoiceName,
    creditNoteName,
    startedAt: new Date().toISOString(),
    screenshots: shots,
    checks: {},
  };
  const browser = await chromium.launch({
    headless: true,
    executablePath: fs.existsSync(chromePath) ? chromePath : undefined,
  });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();
  try {
    await loginOdoo(page);
    await openInvoice(page);
    await page.screenshot({ path: shots.invoice, fullPage: true });
    await openPaymentWizard(page);
    const beforeText = await page.locator('body').innerText();
    result.checks.wizardHasCreditNoteSection = beforeText.includes('Credit Notes Applied in This Payment');
    result.checks.creditNoteVisibleBeforeSelect = beforeText.includes(creditNoteName);
    await page.screenshot({ path: shots.wizardBefore, fullPage: true });

    await selectCreditNote(page);
    const afterSelectText = await page.locator('body').innerText();
    result.checks.amountReducedTo7500 = /7,500\.00|7500\.00|7,500/.test(afterSelectText);
    result.checks.creditNoteAmount2500Visible = /2,500\.00|2500\.00|2,500/.test(afterSelectText);
    result.checks.hasPaymentDifference = /Payment Difference/i.test(afterSelectText);
    result.wizardTextAfterSelectSample = afterSelectText.slice(0, 4000);
    await page.screenshot({ path: shots.wizardAfter, fullPage: true });
    if (!result.checks.amountReducedTo7500) {
      throw new Error('Wizard amount did not reduce to 7,500.00 after selecting CN');
    }

    await createPayment(page);
    await page.waitForTimeout(1500);
    await page.goto(`${baseUrl}/web#action=262&id=${invoiceId}&model=account.move&view_type=form`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.getByText(invoiceName, { exact: false }).first().waitFor({ state: 'visible', timeout: 45000 });
    const finalText = await page.locator('body').innerText().catch(() => '');
    result.finalUrl = page.url();
    result.checks.hasRpcError = /RPC_ERROR|Odoo Server Error|Traceback/i.test(finalText);
    result.finalTextSample = finalText.slice(0, 4000);
    await page.screenshot({ path: shots.afterCreate, fullPage: true });
    if (result.checks.hasRpcError) {
      throw new Error('RPC error appeared after Create Payment');
    }
    result.status = 'passed_ui';
  } catch (error) {
    result.status = 'failed_ui';
    result.error = String(error && error.stack ? error.stack : error);
    await page.screenshot({ path: shots.error, fullPage: true }).catch(() => {});
    process.exitCode = 1;
  } finally {
    result.finishedAt = new Date().toISOString();
    fs.writeFileSync(resultPath, JSON.stringify(result, null, 2));
    fs.writeFileSync(logPath, [
      `UI test: single invoice register payment with selected credit note`,
      `Base URL: ${baseUrl}`,
      `Invoice: ${invoiceName} (${invoiceId})`,
      `Credit Note: ${creditNoteName}`,
      `Status: ${result.status}`,
      `Wizard amount reduced to 7,500: ${result.checks.amountReducedTo7500}`,
      `Credit note visible: ${result.checks.creditNoteVisibleBeforeSelect}`,
      `RPC error: ${result.checks.hasRpcError || false}`,
      `Final URL: ${result.finalUrl || '-'}`,
      `Screenshots:`,
      `- ${shots.invoice}`,
      `- ${shots.wizardBefore}`,
      `- ${shots.wizardAfter}`,
      `- ${shots.afterCreate}`,
      result.error ? `Error: ${result.error}` : '',
    ].filter(Boolean).join('\n'));
    await browser.close();
  }
})();

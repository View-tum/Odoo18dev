const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const baseUrl = process.env.ODOO_URL || 'http://127.0.0.1:8822';
const db = process.env.ODOO_DB || 'GoldMints_Uat_Manu';
const login = process.env.ODOO_LOGIN || 'admin';
const password = process.env.ODOO_PASSWORD || 'admin';
const saleOrderId = Number(process.env.SALE_ORDER_ID);
const saleOrderName = process.env.SALE_ORDER_NAME;
const invoiceId = Number(process.env.INVOICE_ID);
const invoiceName = process.env.INVOICE_NAME;
const creditNoteName = process.env.CREDIT_NOTE_NAME;
const skipBankPayment = process.env.SKIP_BANK_PAYMENT === '1';
const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const root = path.join(__dirname, 'sale_auto_confirm_invoice_cn_payment');

const resultPath = path.join(root, 'result.json');
const logPath = path.join(root, 'chat_log.txt');
const shots = {
  saleOrder: path.join(root, '01_sale_order_before_payment.png'),
  wizardInitial: path.join(root, '02_payment_popup_initial.png'),
  wizardSelected: path.join(root, '03_payment_popup_cn_selected.png'),
  invoiceAfter: path.join(root, '04_invoice_after_payment.png'),
  error: path.join(root, 'error.png'),
};

async function visible(locator, timeout = 5000) {
  try {
    await locator.first().waitFor({ state: 'visible', timeout });
    return true;
  } catch {
    return false;
  }
}

async function clickFirst(locators, timeout = 5000) {
  for (const locator of locators) {
    if (await visible(locator, timeout)) {
      await locator.first().click({ force: true });
      return true;
    }
  }
  return false;
}

async function loginOdoo(page) {
  await page.goto(`${baseUrl}/web/login?db=${encodeURIComponent(db)}`, { waitUntil: 'domcontentloaded' });
  if (await visible(page.locator('input[name="login"]'), 15000)) {
    await page.locator('input[name="login"]').fill(login);
    await page.locator('input[name="password"]').fill(password);
    await Promise.all([
      page.waitForLoadState('networkidle').catch(() => {}),
      page.locator('button[type="submit"], input[type="submit"]').first().click(),
    ]);
  }
  await page.waitForLoadState('networkidle').catch(() => {});
}

async function openSaleOrder(page) {
  await page.goto(`${baseUrl}/web#id=${saleOrderId}&model=sale.order&view_type=form`, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.getByText(saleOrderName, { exact: false }).first().waitFor({ state: 'visible', timeout: 45000 });
}

async function openPaymentWizard(page) {
  const clicked = await clickFirst([
    page.locator('button[name="action_receive_van_sale_payment"]'),
    page.getByRole('button', { name: /ชำระเงิน|Receive Payment/i }),
  ], 15000);
  if (!clicked) {
    throw new Error('Receive payment button was not visible');
  }
  await page.locator('.modal:visible, .o_dialog:visible').first().waitFor({ state: 'visible', timeout: 45000 });
  await page.getByText(/Customer Credit Notes|Create Payment|Receive Payment/i).first().waitFor({ state: 'visible', timeout: 45000 });
}

async function selectCreditNote(page) {
  const modal = page.locator('.modal:visible, .o_dialog:visible').first();
  await modal.getByText(creditNoteName, { exact: false }).first().waitFor({ state: 'visible', timeout: 45000 });
  const row = modal.locator('tr').filter({ hasText: creditNoteName }).first();
  await row.waitFor({ state: 'visible', timeout: 10000 });
  const checkbox = row.locator('input[type="checkbox"]').first();
  await checkbox.waitFor({ state: 'visible', timeout: 10000 });
  await checkbox.check({ force: true });
  await page.waitForTimeout(1500);
}

async function addBankPayment(page) {
  const modal = page.locator('.modal:visible, .o_dialog:visible').first();
  const clicked = await clickFirst([
    modal.getByRole('button', { name: /\+ Bank/i }),
    modal.locator('button').filter({ hasText: '+ Bank' }),
  ], 10000);
  if (!clicked) {
    throw new Error('Bank payment button was not visible');
  }
  await page.waitForTimeout(2000);
}

async function createPayment(page) {
  const clicked = await clickFirst([
    page.locator('.modal-footer button[name="action_receive_mobile_payment"]'),
    page.getByRole('button', { name: /^Create Payment$/i }),
  ], 15000);
  if (!clicked) {
    throw new Error('Create Payment button was not visible');
  }
  await page.waitForTimeout(8000);
}

async function openInvoice(page) {
  await page.goto(`${baseUrl}/web#id=${invoiceId}&model=account.move&view_type=form`, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.getByText(invoiceName, { exact: false }).first().waitFor({ state: 'visible', timeout: 45000 });
}

(async () => {
  fs.mkdirSync(root, { recursive: true });
  const result = {
    baseUrl,
    db,
    saleOrderId,
    saleOrderName,
    invoiceId,
    invoiceName,
    creditNoteName,
    screenshots: shots,
    startedAt: new Date().toISOString(),
    checks: {},
  };
  const browser = await chromium.launch({
    headless: true,
    executablePath: fs.existsSync(chromePath) ? chromePath : undefined,
  });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 } });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  try {
    await loginOdoo(page);
    await openSaleOrder(page);
    await page.screenshot({ path: shots.saleOrder, fullPage: true });
    result.checks.saleOrderOpened = (await page.locator('body').innerText()).includes(saleOrderName);

    await openPaymentWizard(page);
    const initialText = await page.locator('body').innerText();
    result.checks.creditNoteVisible = initialText.includes(creditNoteName);
    result.checks.oldCrossSettlementVisible = initialText.includes('Cross Settlement (AP/AR)');
    result.checks.separateCreditNoteHeaderVisible = initialText.includes('Credit Notes in This Payment');
    result.checks.paymentPreviewVisible = initialText.includes('Payment Journal Items Preview');
    await page.screenshot({ path: shots.wizardInitial, fullPage: true });

    await selectCreditNote(page);
    if (!skipBankPayment) {
      await addBankPayment(page);
    }
    const selectedText = await page.locator('body').innerText();
    result.checks.creditNoteSelectedAmountVisible = /2,500\.00|2,500|2500\.00/.test(selectedText);
    result.checks.bankPaymentVisible = /7,500\.00|7,500|7500\.00/.test(selectedText);
    result.checks.balanceZeroVisible = /Balance:\s*0\.00|Balance\s*0\.00/.test(selectedText);
    result.checks.paymentDifferenceVisible = /Payment Difference/i.test(selectedText);
    await page.screenshot({ path: shots.wizardSelected, fullPage: true });

    if (!result.checks.creditNoteVisible) {
      throw new Error(`Credit note ${creditNoteName} was not visible in payment wizard`);
    }
    if (result.checks.separateCreditNoteHeaderVisible || result.checks.paymentPreviewVisible) {
      throw new Error('Old separate credit note section or payment preview is still visible');
    }
    if (result.checks.paymentDifferenceVisible) {
      throw new Error('Payment Difference appeared in the custom payment wizard');
    }
    if (!skipBankPayment && !result.checks.bankPaymentVisible) {
      throw new Error('Bank payment amount 7,500 was not visible after clicking + Bank');
    }

    await createPayment(page);
    await openInvoice(page);
    const finalText = await page.locator('body').innerText();
    result.checks.rpcErrorVisible = /RPC_ERROR|Odoo Server Error|Traceback/i.test(finalText);
    result.checks.invoicePaidVisible = /Paid|PAID|ชำระแล้ว/i.test(finalText);
    await page.screenshot({ path: shots.invoiceAfter, fullPage: true });
    if (result.checks.rpcErrorVisible) {
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
      'UI test: Van Sales custom Receive Payment with selected customer CN',
      `Base URL: ${baseUrl}`,
      `Sale Order: ${saleOrderName} (${saleOrderId})`,
      `Invoice: ${invoiceName} (${invoiceId})`,
      `Credit Note: ${creditNoteName}`,
      `Status: ${result.status}`,
      `CN visible: ${result.checks.creditNoteVisible}`,
      `CN amount visible after select: ${result.checks.creditNoteSelectedAmountVisible}`,
      `Payment Difference visible: ${result.checks.paymentDifferenceVisible}`,
      `RPC error visible: ${result.checks.rpcErrorVisible || false}`,
      `Invoice paid visible: ${result.checks.invoicePaidVisible || false}`,
      'Screenshots:',
      `- ${shots.saleOrder}`,
      `- ${shots.wizardInitial}`,
      `- ${shots.wizardSelected}`,
      `- ${shots.invoiceAfter}`,
      result.error ? `Error: ${result.error}` : '',
    ].filter(Boolean).join('\n'));
    await browser.close().catch(() => {});
    process.exit(process.exitCode || 0);
  }
})();

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const baseUrl = process.env.ODOO_URL || 'http://127.0.0.1:8814';
const db = process.env.ODOO_DB || 'GoldMints_Uat_Manu';
const login = process.env.ODOO_LOGIN || 'admin';
const password = process.env.ODOO_PASSWORD || 'admin';
const saleOrderId = Number(process.env.SALE_ORDER_ID);
const saleOrderName = process.env.SALE_ORDER_NAME;
const invoiceId = Number(process.env.INVOICE_ID);
const invoiceName = process.env.INVOICE_NAME;
const creditNoteName = process.env.CREDIT_NOTE_NAME;
const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const root = __dirname;

const resultPath = path.join(root, 'sale_payment_cn_cross_settlement_ui_result.json');
const logPath = path.join(root, 'sale_payment_cn_cross_settlement_chat_log.txt');
const shots = {
  saleOrder: path.join(root, 'sale_payment_cn_cross_settlement_01_sale_order.png'),
  wizardBefore: path.join(root, 'sale_payment_cn_cross_settlement_02_wizard_before.png'),
  wizardAfterSelect: path.join(root, 'sale_payment_cn_cross_settlement_03_wizard_after_select.png'),
  invoiceAfterPayment: path.join(root, 'sale_payment_cn_cross_settlement_04_invoice_after_payment.png'),
  error: path.join(root, 'sale_payment_cn_cross_settlement_error.png'),
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
      await locator.first().click({ force: true, timeout: 5000 });
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

async function openSaleOrder(page) {
  await page.goto(`${baseUrl}/web#id=${saleOrderId}&model=sale.order&view_type=form`, {
    waitUntil: 'domcontentloaded',
  });
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.getByText(saleOrderName, { exact: false }).first().waitFor({ state: 'visible', timeout: 45000 });
}

async function openReceivePaymentWizard(page) {
  const clicked = await clickFirst(page, [
    page.locator('button[name="action_receive_van_sale_payment"]'),
    page.locator('button:has-text("ชำระเงิน")'),
    page.getByRole('button', { name: /ชำระเงิน/i }),
    page.getByRole('button', { name: /Receive Payment/i }),
  ], 10000);
  if (!clicked) {
    throw new Error('Receive Payment button was not visible on sale order form');
  }
  await page.locator('.modal:visible, .o_dialog:visible').first().waitFor({ state: 'visible', timeout: 45000 });
  await page.getByText(/Partner Settlement|Cross Settlement|Create Payment|Register Payment/i).first().waitFor({
    state: 'visible',
    timeout: 45000,
  });
}

async function selectCreditNote(page) {
  const modal = page.locator('.modal:visible, .o_dialog:visible').first();
  const partnerSettlementTab = modal.getByRole('tab', { name: /Partner Settlement/i });
  if (await visible(partnerSettlementTab, 3000)) {
    await partnerSettlementTab.click();
  }
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
  await page.waitForTimeout(2500);
}

async function createPayment(page) {
  const clicked = await clickFirst(page, [
    page.locator('.modal-footer button[name="action_create_payments"]'),
    page.locator('.modal-footer button.btn-primary').filter({ hasText: /Create Payment/i }),
    page.getByRole('button', { name: /^Create Payment$/i }),
  ], 10000);
  if (!clicked) {
    throw new Error('Create Payment button was not visible');
  }
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(3500);
}

async function openInvoice(page) {
  await page.goto(`${baseUrl}/web#id=${invoiceId}&model=account.move&view_type=form`, {
    waitUntil: 'domcontentloaded',
  });
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
  try {
    await loginOdoo(page);
    await openSaleOrder(page);
    const saleOrderText = await page.locator('body').innerText();
    result.checks.saleOrderOpened = saleOrderText.includes(saleOrderName);
    result.checks.receivePaymentButtonVisible = /ชำระเงิน|Receive Payment/.test(saleOrderText);
    await page.screenshot({ path: shots.saleOrder, fullPage: true });

    await openReceivePaymentWizard(page);
    const beforeText = await page.locator('body').innerText();
    result.checks.hasPartnerSettlementTab = beforeText.includes('Partner Settlement');
    result.checks.hasCrossSettlementPanel = /Cross Settlement \(AP\/AR\)/i.test(beforeText);
    result.checks.creditNoteVisibleBeforeSelect = beforeText.includes(creditNoteName);
    result.checks.hasOldSeparateCreditNoteHeader = beforeText.includes('Credit Notes in This Payment');
    result.checks.hasPaymentJournalItemsPreviewBefore = beforeText.includes('Payment Journal Items Preview');
    result.wizardBeforeSample = beforeText.slice(0, 5000);
    await page.screenshot({ path: shots.wizardBefore, fullPage: true });

    await selectCreditNote(page);
    const afterSelectText = await page.locator('body').innerText();
    result.checks.amountReducedTo7500 = /7,500\.00|7500\.00|7,500/.test(afterSelectText);
    result.checks.creditNoteAmount2500Visible = /2,500\.00|2500\.00|2,500/.test(afterSelectText);
    result.checks.hasPaymentDifference = /Payment Difference/i.test(afterSelectText);
    result.checks.hasPaymentJournalItemsPreviewAfter = afterSelectText.includes('Payment Journal Items Preview');
    result.wizardAfterSelectSample = afterSelectText.slice(0, 5000);
    await page.screenshot({ path: shots.wizardAfterSelect, fullPage: true });

    if (!result.checks.hasPartnerSettlementTab) {
      throw new Error('Partner Settlement tab was not visible');
    }
    if (!result.checks.hasCrossSettlementPanel) {
      throw new Error('Cross Settlement (AP/AR) panel was not visible');
    }
    if (!result.checks.creditNoteVisibleBeforeSelect) {
      throw new Error(`Credit note ${creditNoteName} was not visible in the wizard`);
    }
    if (result.checks.hasOldSeparateCreditNoteHeader) {
      throw new Error('Old Credit Notes in This Payment section is still visible');
    }
    if (result.checks.hasPaymentJournalItemsPreviewBefore || result.checks.hasPaymentJournalItemsPreviewAfter) {
      throw new Error('Payment Journal Items Preview is still visible');
    }
    if (!result.checks.amountReducedTo7500) {
      throw new Error('Wizard amount did not reduce to 7,500.00 after selecting CN');
    }
    if (result.checks.hasPaymentDifference) {
      throw new Error('Payment Difference appeared after selecting CN');
    }

    await createPayment(page);
    await openInvoice(page);
    const finalText = await page.locator('body').innerText().catch(() => '');
    result.checks.hasRpcError = /RPC_ERROR|Odoo Server Error|Traceback/i.test(finalText);
    result.checks.finalPaid = /PAID|Paid/i.test(finalText);
    result.checks.amountDueZero = /Amount Due\s*0\.00|Amount Due[\s\S]{0,80}0\.00/.test(finalText);
    result.finalTextSample = finalText.slice(0, 5000);
    result.finalUrl = page.url();
    await page.screenshot({ path: shots.invoiceAfterPayment, fullPage: true });
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
      'UI test: Sale Order Receive Payment with CN inside Cross Settlement (AP/AR)',
      `Base URL: ${baseUrl}`,
      `Sale Order: ${saleOrderName} (${saleOrderId})`,
      `Invoice: ${invoiceName} (${invoiceId})`,
      `Credit Note: ${creditNoteName}`,
      `Status: ${result.status}`,
      `Partner Settlement tab: ${result.checks.hasPartnerSettlementTab}`,
      `Cross Settlement panel: ${result.checks.hasCrossSettlementPanel}`,
      `Old CN section visible: ${result.checks.hasOldSeparateCreditNoteHeader}`,
      `JI preview visible before: ${result.checks.hasPaymentJournalItemsPreviewBefore}`,
      `JI preview visible after: ${result.checks.hasPaymentJournalItemsPreviewAfter}`,
      `Amount reduced to 7,500: ${result.checks.amountReducedTo7500}`,
      `Payment Difference visible: ${result.checks.hasPaymentDifference}`,
      `RPC error: ${result.checks.hasRpcError || false}`,
      `Final paid: ${result.checks.finalPaid || false}`,
      `Final amount due zero: ${result.checks.amountDueZero || false}`,
      'Screenshots:',
      `- ${shots.saleOrder}`,
      `- ${shots.wizardBefore}`,
      `- ${shots.wizardAfterSelect}`,
      `- ${shots.invoiceAfterPayment}`,
      result.error ? `Error: ${result.error}` : '',
    ].filter(Boolean).join('\n'));
    await Promise.race([
      browser.close(),
      new Promise((resolve) => setTimeout(resolve, 5000)),
    ]).catch(() => {});
    process.exit(process.exitCode || 0);
  }
})();

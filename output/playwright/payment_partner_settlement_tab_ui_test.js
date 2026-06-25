const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const baseUrl = process.env.ODOO_URL || 'http://127.0.0.1:8811';
const db = process.env.ODOO_DB || 'GoldMints_Uat_Manu';
const login = process.env.ODOO_LOGIN || 'admin';
const password = process.env.ODOO_PASSWORD || 'admin';
const invoiceId = Number(process.env.INVOICE_ID);
const invoiceName = process.env.INVOICE_NAME;
const creditNoteName = process.env.CREDIT_NOTE_NAME;
const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const root = __dirname;
const resultPath = path.join(root, 'payment_partner_settlement_tab_ui_result.json');
const logPath = path.join(root, 'payment_partner_settlement_tab_chat_log.txt');

const shots = {
  invoice: path.join(root, 'payment_partner_settlement_tab_01_invoice.png'),
  wizardBefore: path.join(root, 'payment_partner_settlement_tab_02_wizard_before.png'),
  wizardAfterSelect: path.join(root, 'payment_partner_settlement_tab_03_wizard_after_select.png'),
  afterCreate: path.join(root, 'payment_partner_settlement_tab_04_after_create_payment.png'),
  error: path.join(root, 'payment_partner_settlement_tab_error.png'),
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
    page.locator('button[name="action_register_payment"]'),
  ], 8000);
  if (!clicked) {
    throw new Error('Payment button was not visible on invoice form');
  }
  await page.locator('.modal:visible, .o_dialog:visible').first().waitFor({ state: 'visible', timeout: 45000 });
  await page.getByText(/Partner Settlement|Create Payment|Register Payment/i).first().waitFor({
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
  await page.waitForTimeout(3000);
}

async function readPaymentPreview(page) {
  const modal = page.locator('.modal:visible, .o_dialog:visible').first();
  const previewHeader = modal.getByText(/Payment Journal Items Preview/i).first();
  await previewHeader.waitFor({ state: 'attached', timeout: 15000 });
  await previewHeader.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1000);
  const modalText = await modal.innerText();
  const headerIndex = modalText.search(/Payment Journal Items Preview/i);
  const allocationIndex = modalText.search(/Invoices Allocation/i);
  return headerIndex >= 0
    ? modalText.slice(headerIndex, allocationIndex > headerIndex ? allocationIndex : undefined)
    : modalText;
}

async function createPayment(page) {
  const clicked = await clickFirst(page, [
    page.locator('.modal-footer button[name="action_create_payments"]'),
    page.locator('.modal-footer button.btn-primary').filter({ hasText: /Create Payment/i }),
    page.getByRole('button', { name: /^Create Payment$/i }),
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
    await openInvoice(page);
    await page.screenshot({ path: shots.invoice, fullPage: true });

    await openPaymentWizard(page);
    const beforeText = await page.locator('body').innerText();
    result.checks.hasPartnerSettlementTab = beforeText.includes('Partner Settlement');
    result.checks.hasOldSeparateCreditNoteHeader = beforeText.includes('Credit Notes Applied in This Payment');
    result.checks.creditNoteVisibleBeforeSelect = beforeText.includes(creditNoteName);
    await page.screenshot({ path: shots.wizardBefore, fullPage: true });

    await selectCreditNote(page);
    const afterSelectText = await page.locator('body').innerText();
    const previewText = await readPaymentPreview(page);
    result.checks.amountReducedTo7500 = /7,500\.00|7500\.00|7,500/.test(afterSelectText);
    result.checks.hasPaymentJournalItemsPreview = /Payment Journal Items Preview/i.test(afterSelectText);
    result.checks.hasDebitCreditColumns = /Debit/i.test(previewText) && /Credit/i.test(previewText);
    result.checks.hasCreditNoteJournalLine = previewText.includes(`Credit Note ${creditNoteName}`);
    result.checks.previewHasCashLine7500 = /7,500\.00|7500\.00|7,500/.test(previewText);
    result.checks.previewHasInvoiceLine10000 = /10,000\.00|10000\.00|10,000/.test(previewText);
    result.checks.previewHasCreditNoteLine2500 = /2,500\.00|2500\.00|2,500/.test(previewText);
    result.checks.hasPaymentDifference = /Payment Difference/i.test(afterSelectText);
    result.wizardTextAfterSelectSample = afterSelectText.slice(0, 5000);
    result.previewText = previewText;
    await page.screenshot({ path: shots.wizardAfterSelect, fullPage: true });

    if (!result.checks.hasPartnerSettlementTab) {
      throw new Error('Partner Settlement tab was not visible');
    }
    if (result.checks.hasOldSeparateCreditNoteHeader) {
      throw new Error('Old separate Credit Notes Applied header is still visible');
    }
    if (!result.checks.amountReducedTo7500) {
      throw new Error('Wizard amount did not reduce to 7,500.00 after selecting CN');
    }
    if (!result.checks.hasPaymentJournalItemsPreview || !result.checks.hasDebitCreditColumns) {
      throw new Error('Payment Journal Items Preview with Debit/Credit was not visible');
    }
    if (!result.checks.previewHasCashLine7500 || !result.checks.previewHasInvoiceLine10000 || !result.checks.previewHasCreditNoteLine2500) {
      throw new Error(`Payment Journal Items Preview totals are incorrect:\n${previewText}`);
    }

    await createPayment(page);
    await page.waitForTimeout(1500);
    await page.goto(`${baseUrl}/web#action=262&id=${invoiceId}&model=account.move&view_type=form`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.getByText(invoiceName, { exact: false }).first().waitFor({ state: 'visible', timeout: 45000 });
    const finalText = await page.locator('body').innerText().catch(() => '');
    result.checks.hasRpcError = /RPC_ERROR|Odoo Server Error|Traceback/i.test(finalText);
    result.checks.finalPaid = /PAID|Paid/i.test(finalText);
    result.checks.amountDueZero = /Amount Due\s*0\.00|Amount Due[\s\S]{0,80}0\.00/.test(finalText);
    result.finalTextSample = finalText.slice(0, 5000);
    result.finalUrl = page.url();
    await page.screenshot({ path: shots.afterCreate, fullPage: true });
    if (result.checks.hasRpcError) {
      throw new Error('RPC error appeared after Create Payment');
    }
    if (!result.checks.finalPaid || !result.checks.amountDueZero) {
      throw new Error('Invoice did not end as Paid with Amount Due 0.00');
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
      'UI test: account_partner_settlement tab with embedded CN and JI preview',
      `Base URL: ${baseUrl}`,
      `Invoice: ${invoiceName} (${invoiceId})`,
      `Credit Note: ${creditNoteName}`,
      `Status: ${result.status}`,
      `Partner Settlement tab: ${result.checks.hasPartnerSettlementTab}`,
      `Old separate CN header visible: ${result.checks.hasOldSeparateCreditNoteHeader}`,
      `Amount reduced to 7,500: ${result.checks.amountReducedTo7500}`,
      `JI preview visible: ${result.checks.hasPaymentJournalItemsPreview}`,
      `Debit/Credit visible: ${result.checks.hasDebitCreditColumns}`,
      `JI preview cash 7,500: ${result.checks.previewHasCashLine7500}`,
      `JI preview invoice 10,000: ${result.checks.previewHasInvoiceLine10000}`,
      `JI preview CN 2,500: ${result.checks.previewHasCreditNoteLine2500}`,
      `RPC error: ${result.checks.hasRpcError || false}`,
      `Final paid: ${result.checks.finalPaid || false}`,
      `Final amount due zero: ${result.checks.amountDueZero || false}`,
      'Screenshots:',
      `- ${shots.invoice}`,
      `- ${shots.wizardBefore}`,
      `- ${shots.wizardAfterSelect}`,
      `- ${shots.afterCreate}`,
      result.error ? `Error: ${result.error}` : '',
    ].filter(Boolean).join('\n'));
    await browser.close();
  }
})();

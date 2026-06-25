# BOT Average Buying Transfer Currency Rate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a safe selectable Odoo provider that imports BOT daily `buying_transfer` rates into standard company currency rates.

**Architecture:** A new addon extends `res.company.currency_provider` with one additional provider and implements the parser contract already used by `currency_rate_live`. A transient settings field stores the BOT API key in system parameters, while an inherited settings view exposes the key only for the new provider. No existing provider, manual rate behavior, accounting model, or official addon is replaced.

**Tech Stack:** Odoo 18 Enterprise, Python, XML inherited views, BOT Exchange Rates API, Odoo `TransactionCase`.

---

### Task 1: Add Failing Provider Contract Tests

**Files:**
- Create: `custom/goldmints_addon-main/currency_rate_bot_buying_transfer/__init__.py`
- Create: `custom/goldmints_addon-main/currency_rate_bot_buying_transfer/__manifest__.py`
- Create: `custom/goldmints_addon-main/currency_rate_bot_buying_transfer/tests/__init__.py`
- Create: `custom/goldmints_addon-main/currency_rate_bot_buying_transfer/tests/test_bot_buying_transfer.py`

- [ ] **Step 1: Create the installable test scaffold and tests**

Create a test module depending on `currency_rate_live`, with tests asserting that:

```python
providers = dict(self.env["res.company"]._fields["currency_provider"].selection)
self.assertIn("bot", providers)
self.assertIn("bot_buying_transfer", providers)
```

```python
rates = self.company._parse_bot_buying_transfer_data(self.active_currencies)
self.assertAlmostEqual(rates["USD"][0], 1.0 / 32.1234)
self.assertEqual(rates["USD"][1], "2026-05-25")
self.assertEqual(rates["THB"], (1.0, "2026-05-25"))
```

```python
with self.assertRaises(UserError):
    self.company._parse_bot_buying_transfer_data(self.active_currencies)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
& '.\.venv\Scripts\python.exe' '.\server\odoo-bin' -c '.\server\odoo.conf' -d test_currency_rate_bot_buying_transfer -i currency_rate_bot_buying_transfer --test-enable --test-tags /currency_rate_bot_buying_transfer --stop-after-init
```

Expected: fail because the additional provider and parser method do not exist yet.

### Task 2: Implement The BOT Buying Transfer Provider

**Files:**
- Create: `custom/goldmints_addon-main/currency_rate_bot_buying_transfer/models/__init__.py`
- Create: `custom/goldmints_addon-main/currency_rate_bot_buying_transfer/models/res_company.py`

- [ ] **Step 1: Extend the provider selection and implement parser**

Implement `bot_buying_transfer` as an additive `selection_add` value and implement `_parse_bot_buying_transfer_data()` which:

```python
response = requests.get(
    BOT_DAILY_AVERAGE_ENDPOINT,
    headers={"Authorization": api_key, "Accept": "application/json"},
    params={"start_period": start_date, "end_period": end_date},
    timeout=30,
)
```

The method must filter active currencies, select the latest ISO period returned, convert BOT THB-per-foreign-currency values to Odoo rate format with `1.0 / buying_transfer`, and add `THB` as `1.0` for that latest period.

- [ ] **Step 2: Run provider tests to verify GREEN**

Run the test command from Task 1.

Expected: provider parsing tests pass.

### Task 3: Expose Secure Configuration In Existing Settings

**Files:**
- Create: `custom/goldmints_addon-main/currency_rate_bot_buying_transfer/models/res_config_settings.py`
- Create: `custom/goldmints_addon-main/currency_rate_bot_buying_transfer/views/res_config_settings_views.xml`
- Modify: `custom/goldmints_addon-main/currency_rate_bot_buying_transfer/__manifest__.py`
- Modify: `custom/goldmints_addon-main/currency_rate_bot_buying_transfer/models/__init__.py`

- [ ] **Step 1: Add API key settings field**

Add a `Char` setting persisted with:

```python
config_parameter="currency_rate_bot_buying_transfer.api_key"
```

- [ ] **Step 2: Add inherited settings view**

Inherit `currency_rate_live.res_config_settings_view_form` and add the password field immediately under the Service row, visible and required only when `currency_provider == "bot_buying_transfer"`.

- [ ] **Step 3: Run module tests and installation validation**

Run:

```powershell
& '.\.venv\Scripts\python.exe' '.\server\odoo-bin' -c '.\server\odoo.conf' -d test_currency_rate_bot_buying_transfer -u currency_rate_bot_buying_transfer --test-enable --test-tags /currency_rate_bot_buying_transfer --stop-after-init
```

Expected: exit code `0` with no failed tests.

### Task 4: Verify UI And Non-Activation Safety

**Files:**
- No additional files.

- [ ] **Step 1: Install or upgrade on the target development database without changing provider**

Install the module while leaving the current selected Service as `[TH] Bank of Thailand`.

- [ ] **Step 2: Verify actual UI path**

Open:

`Accounting > Configuration > Settings > Accounting > Currencies > Automatic Currency Rates`

Confirm the service list contains `[TH] BOT - Average Buying Transfer Rate`, that the current Service remains unchanged until deliberately selected, and that selecting the new service displays the masked `BOT API Key` field.

- [ ] **Step 3: Configure and validate only after API key is available**

Enter a valid BOT API key, select the new service, press `Update now`, and confirm the latest `buying_transfer` rate entries before enabling scheduled updates.

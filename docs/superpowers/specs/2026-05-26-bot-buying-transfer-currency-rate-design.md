# BOT Average Buying Transfer Currency Rate Design

## Goal

Add a selectable Odoo currency rate provider that imports the Bank of Thailand daily `buying_transfer` rate into standard `res.currency.rate`, while preserving the existing Odoo BOT provider and all existing manual currency-rate customizations.

## Standard Vs Pain Point

### Standard

The installed Odoo `currency_rate_live` module already exposes the actual UI flow `Accounting > Configuration > Settings > Accounting > Currencies > Automatic Currency Rates`, stores rates through standard `res.currency.rate`, and includes the provider `[TH] Bank of Thailand`.

### Pain Point

The standard BOT provider calls the Odoo IAP proxy and receives one unnamed `rate`. It does not let accounting select or audit BOT `buying_transfer`. The official BOT API exposes `buying_sight`, `buying_transfer`, `selling`, and `mid_rate`, so the required accounting basis cannot be guaranteed through the existing standard provider.

## Scope

Create a new custom addon named `currency_rate_bot_buying_transfer` under `custom/goldmints_addon-main`.

The addon will:

- Depend only on `currency_rate_live`.
- Add a new service choice: `[TH] BOT - Average Buying Transfer Rate`.
- Add a masked `BOT API Key` setting visible only when the new service is selected.
- Call the official BOT daily average exchange-rate endpoint using an API key stored through `ir.config_parameter`.
- Read only the `buying_transfer` value for active currencies.
- Return rate data to the standard `currency_rate_live` generation flow, allowing standard cron and `Update now` behavior to remain unchanged.
- Fetch a rolling date range and use the latest returned business date, so weekends and Thai holidays do not prevent a daily scheduled update.

The addon will not:

- Modify `server/odoo/addons/currency_rate_live` or any other official addon.
- Override or change the behavior of `[TH] Bank of Thailand`.
- Modify the installed manual exchange rate customizations.
- Automatically switch the current company to the new provider without configuration and API-key validation.

## Accounting Impact

Once selected, the new provider writes a single standard company currency rate source. The resulting `buying_transfer` rate is therefore used by all transactions that rely on standard rates, including both AR and AP foreign-currency accounting. This matches the confirmed requirement to use one buying-transfer rate system-wide.

## Safety And Error Handling

- A missing API key blocks update with a user-facing configuration error.
- HTTP failures, invalid responses, or empty valid rate data block update instead of writing partial or fabricated rates.
- The source makes a single API request and filters active currencies locally.
- Existing provider selection remains available for rollback from the same settings screen.

## Verification

- Unit tests verify the new provider selection is additive and does not remove the standard BOT provider.
- Unit tests mock BOT data and verify only `buying_transfer` is converted into Odoo rates.
- Unit tests verify missing API key and responses without usable buying-transfer rates fail safely.
- Module upgrade and UI verification confirm that the additional service and key field appear in the actual settings page without selecting the new provider by default.

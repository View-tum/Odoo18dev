# Local UAT Transfer Audit 2026-04-07

Database: `uat` on localhost:5811

## Result

Checked the same transfer-route gaps that were fixed on server 14.

### Verified clean on local UAT
- Packaging RM with `Auto Transfer RM (Plastic)` but missing `Auto Transfer RM (Packaging)`: `0`
- `All / SFG / ?????` with `Manufacture (Pharma)` but missing `Auto Transfer Semi (Pharma)`: `0`
- `All / RM / ???????` with `Buy` but missing `Auto Transfer RM (Pharma)`: `0`

## Conclusion

For the transfer setup issue that was under review, local `uat` is already aligned. No additional route data fix was needed on local at the time of this audit.

## Local focus from now on
- Use local database `uat`
- Odoo config: `C:/365_project/TheCool18e/Dev/server/odoo.conf`
- PostgreSQL: `localhost:5811`
- HTTP: `localhost:8811`

# GUSA Custom

Frappe/ERPNext custom app for Vietnam operations workflows:

- Sales payment claims from Sales to Accounting
- Draft Payment Entry creation with server-side validation
- COD and carrier settlement reconciliation
- Bank statement import and manual matching foundation

Target stack: Frappe/ERPNext v16.

## Deployment Notes

This app is intended for a Frappe Cloud Private Bench. The current workspace does
not include a local bench, so the app is scaffolded as source code and must be
installed on a bench before migration/testing.

The app keeps the current test-site DocType names:

- `Sales Payment Claim`
- `Carrier Settlement`
- `Carrier Settlement Line`

This preserves existing records during migration.

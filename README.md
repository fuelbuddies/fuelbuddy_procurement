### Fuelbuddy Procurement

Buying-side customisations for FuelBuddy ERPNext. First (and so far only) feature: **PARC**.

Purchase Advance Receipt Control (PARC): one row per supplier advance paid against a
Purchase Order, closed when the matching Purchase Receipt is submitted.

Code-first port of the customisations that lived in the site DB (custom DocType in the
*Buying* module plus three DocType-Event Server Scripts). Extracted from the prod restore on
2026-09-22.

| Server Script (DB)                                | Ref DocType      | Event           | -> handler (doctype controller module)     |
|---------------------------------------------------|------------------|-----------------|--------------------------------------------|
| Purchase Advance Receipt Control Payment Entry    | Payment Entry    | After Submit    | `create_parc_on_payment_entry` (on_submit) |
| Purchase Advance Receipt Control -  Warning       | Purchase Receipt | Before Validate | `warn_qty_mismatch_on_purchase_receipt`    |
| Purchase Advance Receipt Control Purchase Receipt | Purchase Receipt | After Submit    | `close_parc_on_purchase_receipt`           |

Changes from the DB scripts (2026-09-22 review):

- **Cancel handlers (new).** Payment Entry `on_cancel` deletes the draft PARCs it opened;
  Purchase Receipt `on_cancel` cancels the PARC it closed and re-inserts a fresh draft so the
  advance is pending again. Before this, a receipt that had closed a PARC could not be
  cancelled at all (Frappe's back-link check), and a cancelled advance left an orphan draft.
- **One matcher for warn and close.** The warning used to compare the *sum* of every draft
  PARC against one receipt line, so a PO with two pending advances warned on every receipt.
  Both handlers now use the same rule: closest draft within +/-20%, oldest wins ties. The
  warning fires only when that match is not exact (or when nothing is in range).
- **Receipt qty is summed per PO** across item lines, so one receipt closes one PARC per PO.
- **`qty_left_to_be_received_from_po`** on close is `PO qty - received to date`; the old
  formula ignored earlier receipts.
- **Atomic close.** `parc.submit()` alone instead of `save()` then `submit()`; a failing
  submit no longer leaves a half-updated draft.
- Currency in the warning table comes from the receipt (`fmt_money`), not a hardcoded `AED`.
- Dropped: the debug `msgprint(alert=True)` lines and the dead `advance_against_po_summary`
  key (no such field).

### Tests

`test_purchase_advance_receipt_control.py` has 18 tests: pure checks on the matcher, the
per-PO aggregation, the warning HTML and the Payment Entry filters, plus 14 lifecycle tests
against a real site (single and double advances, exact / near / out-of-range / multi-line
receipts, message-log assertions, receipt cancel and re-receive, payment cancel allowed and
blocked). Each lifecycle test copies the site's latest submitted PO so company-specific
mandatory fields come along. Everything is rolled back.

```bash
bench --site <site> execute fuelbuddy_procurement.fuelbuddy_procurement.doctype.purchase_advance_receipt_control.test_purchase_advance_receipt_control.run
```

### DB script equivalents

`db_scripts/` holds the same five handlers as pasteable Server Script bodies (for a site that cannot
take the app yet), plus a Purchase Receipt Client Script that shows pending PARC advances on the form.
See `db_scripts/README.md` for names, events and the one-mechanism-at-a-time rule.

### Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/shantanumishra-FB/fuelbuddy_procurement.git --branch main
bench install-app fuelbuddy_procurement
```

`bench migrate` adopts the existing custom DocType **Purchase Advance Receipt Control** into this
app's module (data untouched) and the `after_install` hook disables the three Server Scripts
above so nothing runs twice. Delete them from the DB once the app is live.

Record names (`PARC-26-27-000000001`) come from the site's **Document Naming Rule** (prefix
`PARC.-.FY.-.`, 9 digits). That is data, not part of this app, and keeps working unchanged.

### License

mit

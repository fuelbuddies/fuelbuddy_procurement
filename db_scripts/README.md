### DB script equivalents

Same behaviour as the app's controller handlers, as pasteable **Server Script** bodies for a site
that cannot take the app yet (prod today). Bodies are written for the Server Script sandbox: no
imports, no `str.format`, no `_`-prefixed names. Keep either the app **or** these enabled, never
both; `after_install` disables all five by name.

| Server Script name (paste as-is)                          | Ref DocType      | Event           | Body |
|-----------------------------------------------------------|------------------|-----------------|------|
| Purchase Advance Receipt Control Payment Entry            | Payment Entry    | After Submit    | `server_scripts/parc_payment_entry_after_submit.py` |
| Purchase Advance Receipt Control Payment Entry Cancel     | Payment Entry    | After Cancel    | `server_scripts/parc_payment_entry_after_cancel.py` |
| Purchase Advance Receipt Control -  Warning               | Purchase Receipt | Before Validate | `server_scripts/parc_purchase_receipt_before_validate.py` |
| Purchase Advance Receipt Control Purchase Receipt         | Purchase Receipt | After Submit    | `server_scripts/parc_purchase_receipt_after_submit.py` |
| Purchase Advance Receipt Control Purchase Receipt Cancel  | Purchase Receipt | After Cancel    | `server_scripts/parc_purchase_receipt_after_cancel.py` |

The first, third and fourth names match the legacy prod scripts (note the double space in
"Control -  Warning"), so pasting the body over the existing record is an in-place upgrade.

| Client Script name                                | DocType          | View | Body |
|---------------------------------------------------|------------------|------|------|
| Purchase Advance Receipt Control - PR Dashboard   | Purchase Receipt | Form | `client_scripts/purchase_receipt_parc.js` |

The client script is UI only (headline with pending advances per PO, link to the closed PARC after
submit, a View > PARC button). It has no server-side effect and works with either the app or the
server scripts. Nothing is needed on the PARC form itself: every field is read-only.

`TestServerScriptsLifecycle` in the app's test module loads these five bodies into Server Script
records, switches the app handlers off, and re-runs every lifecycle test through the sandbox.

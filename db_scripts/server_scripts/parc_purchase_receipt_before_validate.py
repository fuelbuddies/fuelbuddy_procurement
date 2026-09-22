# Server Script | Purchase Receipt | Before Validate | "Purchase Advance Receipt Control -  Warning"
# Warn when this receipt will not close a draft PARC exactly. Never blocks.
# Sandbox rules: no tuple unpacking (no _unpack_sequence_ guard), and no comprehensions or
# lambdas that use top-level names (they compile to nested scopes that cannot see script locals).
TOL = 0.20
EPS = 0.01
flt = frappe.utils.flt
EXP = "qty_to_be_received_against_the_advance_paid"

qty_by_po = {}
for item in doc.items:
    if item.purchase_order:
        qty_by_po[item.purchase_order] = qty_by_po.get(item.purchase_order, 0) + flt(item.qty)

for po in qty_by_po:
    qty = qty_by_po[po]
    parcs = frappe.get_all("Purchase Advance Receipt Control",
                           filters={"purchase_order": po, "docstatus": 0},
                           fields=["name", EXP, "payment_entry", "advance_paid", "creation"],
                           order_by="creation asc")
    if not parcs:
        continue
    best = None
    best_gap = None
    for p in parcs:
        gap = abs(flt(p[EXP]) - qty)
        if gap <= qty * TOL and (best is None or gap < best_gap):  # parcs are creation asc: ties keep the oldest
            best = p
            best_gap = gap
    if best and best_gap <= EPS:
        continue

    td = "border:1px solid #dee2e6;padding:8px;"
    rows = ""
    for p in parcs:
        rows += (f"<tr><td style='{td}'><b>{p.name}</b></td>"
                 f"<td style='{td}'>{frappe.utils.format_datetime(p.creation, 'dd-MM-yyyy hh:mm:ss a')}</td>"
                 f"<td style='{td}'>{p.payment_entry or 'N/A'}</td>"
                 f"<td style='{td}text-align:right;'>{frappe.utils.fmt_money(p.advance_paid, currency=doc.currency)}</td>"
                 f"<td style='{td}text-align:right;'>{flt(p[EXP]):.2f}</td></tr>")
    if best:
        verdict = (f"<b style='color:#0066cc;'>Closest PARC: {best.name} (expected {flt(best[EXP]):.2f})</b><br>"
                   f"<b style='color:#dc3545;'>Difference: {qty - flt(best[EXP]):.2f}</b><br>")
    else:
        verdict = "<b style='color:#dc3545;'>No draft PARC within &plusmn;20% of this quantity; none will be closed.</b><br>"
    html = (f"<b>&#9888; Purchase Order: {po}</b><br><br>"
            f"<b>Purchase Receipt Quantity: {qty:.2f}</b><br><br>"
            "<b>Related PARC Records (Draft Only):</b><br>"
            "<table style='width:100%;border-collapse:collapse;margin-top:10px;'>"
            "<tr style='background-color:#f8f9fa;'>"
            f"<th style='{td}text-align:left;'>PARC Number</th><th style='{td}text-align:left;'>Date &amp; Time</th>"
            f"<th style='{td}text-align:left;'>Payment Entry</th><th style='{td}text-align:right;'>Payment Amount</th>"
            f"<th style='{td}text-align:right;'>Expected Qty</th></tr>{rows}</table><br>"
            f"{verdict}<br><i>You can still submit this Purchase Receipt.</i>")
    frappe.msgprint(msg=html, title="Quantity Mismatch Warning", indicator="orange")

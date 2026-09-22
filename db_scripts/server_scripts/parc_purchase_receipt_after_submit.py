# Server Script | Purchase Receipt | After Submit | "Purchase Advance Receipt Control Purchase Receipt"
# Close the best-matching draft PARC per Purchase Order: within +/-20%, closest first, oldest wins ties.
# Sandbox rules: no tuple unpacking (no _unpack_sequence_ guard), and no comprehensions or
# lambdas that use top-level names (they compile to nested scopes that cannot see script locals).
TOL = 0.20
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
                           fields=["name", EXP, "creation"], order_by="creation asc")
    if not parcs:
        continue
    best = None
    best_gap = None
    for p in parcs:
        gap = abs(flt(p[EXP]) - qty)
        if gap <= qty * TOL and (best is None or gap < best_gap):  # parcs are creation asc: ties keep the oldest
            best = p
            best_gap = gap
    if not best:
        frappe.msgprint(f"No PARC found within &plusmn;20% range for PO: {po}<br>"
                        f"Receipt Qty: {qty:.2f} (Range: {qty - qty * TOL:.2f} - {qty + qty * TOL:.2f})",
                        alert=True, indicator="orange")
        continue
    try:
        parc = frappe.get_doc("Purchase Advance Receipt Control", best.name)
        parc.purchase_receipt = doc.name
        parc.qty_of_pr = qty
        parc.grand_total_of_pr = doc.grand_total
        # received-to-date already includes this receipt (docstatus is 1 by After Submit)
        received = flt(frappe.db.get_value(
            "Purchase Receipt Item", {"purchase_order": po, "docstatus": 1}, "sum(qty)"))
        parc.qty_left_to_be_received_from_po = flt(parc.qty_of_po) - received
        parc.flags.ignore_permissions = True
        parc.submit()  # one save: no half-updated draft if submit fails
        frappe.msgprint(f"PARC {best.name} updated and submitted<br>PO: {po}<br>"
                        f"Expected Qty: {flt(best[EXP]):.2f}, Actual Qty: {qty:.2f}",
                        alert=True, indicator="green")
    except Exception as e:
        # a PARC that will not submit must not block the Purchase Receipt
        frappe.msgprint(f"Error submitting PARC: {e}", alert=True, indicator="red")
        frappe.log_error(f"PARC Submit Error: {e}", "PARC Submission Failed")

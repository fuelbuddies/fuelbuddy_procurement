# Server Script | Payment Entry | After Submit | "Purchase Advance Receipt Control Payment Entry"
# One draft PARC per Purchase Order reference on a supplier advance.
flt = frappe.utils.flt
if doc.payment_type == "Pay" and doc.party_type == "Supplier":
    for ref in doc.references:
        if ref.reference_doctype != "Purchase Order" or flt(ref.allocated_amount) <= 0:
            continue
        po = frappe.get_doc("Purchase Order", ref.reference_name)
        if not po.items:
            continue
        item = po.items[0]  # fuel POs carry one line, as the original script assumed
        grand_total = flt(po.grand_total)
        pct = flt(ref.allocated_amount) / grand_total if grand_total > 0 else 0
        qty_adv = flt(item.qty) * pct
        received = flt(frappe.db.get_value(
            "Purchase Receipt Item", {"purchase_order": po.name, "docstatus": 1}, "sum(qty)"))
        frappe.get_doc({
            "doctype": "Purchase Advance Receipt Control",
            "payment_entry": doc.name,
            "purchase_order": po.name,
            "qty_of_po": item.qty,
            "uom_of_item": item.uom,
            "rate_of_po": item.rate,
            "grand_total_of_po": po.grand_total,
            "advance_against_po__summary_": po.advance_paid,
            "advance_paid": ref.allocated_amount,
            "qty_to_be_received_against_the_advance_paid": qty_adv,
            "qty_left_to_be_received_from_po": flt(item.qty) - qty_adv - received,
        }).insert(ignore_permissions=True)

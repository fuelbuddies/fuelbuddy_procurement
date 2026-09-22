# Server Script | Purchase Receipt | After Cancel | "Purchase Advance Receipt Control Purchase Receipt Cancel"
# Cancel the PARC this receipt closed and re-open the advance as a fresh draft. After Cancel runs
# before Frappe's back-link check, so this is what lets the receipt cancel at all.
flt = frappe.utils.flt
EXP = "qty_to_be_received_against_the_advance_paid"
for name in frappe.get_all("Purchase Advance Receipt Control",
                           filters={"purchase_receipt": doc.name, "docstatus": 1}, pluck="name"):
    parc = frappe.get_doc("Purchase Advance Receipt Control", name)
    parc.flags.ignore_permissions = True
    parc.cancel()
    draft = frappe.copy_doc(parc)
    draft.docstatus = 0  # copy_doc keeps the source's (now cancelled) docstatus
    draft.purchase_receipt = None
    draft.qty_of_pr = None
    draft.grand_total_of_pr = None
    received = flt(frappe.db.get_value(
        "Purchase Receipt Item", {"purchase_order": parc.purchase_order, "docstatus": 1}, "sum(qty)"))
    draft.qty_left_to_be_received_from_po = flt(parc.qty_of_po) - flt(parc.get(EXP)) - received
    draft.insert(ignore_permissions=True)

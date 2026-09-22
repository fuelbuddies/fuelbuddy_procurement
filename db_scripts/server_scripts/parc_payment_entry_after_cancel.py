# Server Script | Payment Entry | After Cancel | "Purchase Advance Receipt Control Payment Entry Cancel"
# Drop the draft PARCs this advance opened. A PARC already closed by a receipt blocks the
# cancel through Frappe's normal link check, which is the right outcome.
for name in frappe.get_all("Purchase Advance Receipt Control",
                           filters={"payment_entry": doc.name, "docstatus": 0}, pluck="name"):
    frappe.delete_doc("Purchase Advance Receipt Control", name, ignore_permissions=True)

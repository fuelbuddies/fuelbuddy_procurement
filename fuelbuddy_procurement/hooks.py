app_name = "fuelbuddy_procurement"
app_title = "Fuelbuddy Procurement"
app_publisher = "Fuelbuddy"
app_description = "Procurement customisations: Purchase Advance Receipt Control (PARC)"
app_email = "shantanu.mishra@fuelbuddy.in"
app_license = "mit"

after_install = "fuelbuddy_procurement.install.after_install"

_PARC = "fuelbuddy_procurement.fuelbuddy_procurement.doctype.purchase_advance_receipt_control.purchase_advance_receipt_control"

# Submit/validate handlers ported from the DB Server Scripts of the same names (see README).
# Server-script event labels map to controller hooks: "After Submit" -> on_submit,
# "Before Validate" -> before_validate. The on_cancel handlers are new: the scripts never
# unwound a PARC when its Payment Entry or Purchase Receipt was cancelled.
doc_events = {
	"Payment Entry": {
		"on_submit": f"{_PARC}.create_parc_on_payment_entry",
		"on_cancel": f"{_PARC}.delete_draft_parcs_on_payment_entry_cancel",
	},
	"Purchase Receipt": {
		"before_validate": f"{_PARC}.warn_qty_mismatch_on_purchase_receipt",
		"on_submit": f"{_PARC}.close_parc_on_purchase_receipt",
		"on_cancel": f"{_PARC}.reopen_parc_on_purchase_receipt_cancel",
	},
}

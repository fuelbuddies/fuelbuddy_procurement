"""Disable the three DB Server Scripts this app replaces, so the logic does not run twice.

Runs from the ``after_install`` hook (a patch would not: ``bench install-app`` marks a new app's patches as already applied instead of executing them).
"""

import frappe

# The three legacy prod scripts plus the two cancel scripts in db_scripts/ (same behaviour as this
# app, for sites that cannot take the app yet). Only one of the two mechanisms may be enabled.
LEGACY_SERVER_SCRIPTS = [
	"Purchase Advance Receipt Control -  Warning",
	"Purchase Advance Receipt Control Payment Entry",
	"Purchase Advance Receipt Control Payment Entry Cancel",
	"Purchase Advance Receipt Control Purchase Receipt",
	"Purchase Advance Receipt Control Purchase Receipt Cancel",
]


def after_install():
	for name in LEGACY_SERVER_SCRIPTS:
		if frappe.db.exists("Server Script", name):
			frappe.db.set_value("Server Script", name, "disabled", 1)
	frappe.cache.delete_value("server_script_map")

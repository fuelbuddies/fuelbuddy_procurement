# Copyright (c) 2026, Fuelbuddy and contributors
# For license information, please see license.txt

"""Purchase Advance Receipt Control (PARC).

One PARC row per supplier advance: created when a Payment Entry (Pay -> Supplier) is
submitted against a Purchase Order, and closed (submitted) when the matching Purchase
Receipt arrives. Cancelling the Purchase Receipt cancels the PARC and re-opens the advance
as a fresh draft; cancelling the Payment Entry deletes its draft PARCs (a PARC already
closed by a receipt blocks the cancel through Frappe's normal link check).

``hooks.py`` ``doc_events`` wires the handlers onto Payment Entry / Purchase Receipt.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, fmt_money, format_datetime

# A Purchase Receipt closes a draft PARC whose expected qty is within +/-20% of the received qty.
MATCH_TOLERANCE = 0.20
# Below this, expected vs received qty is treated as equal (float dust).
QTY_EPSILON = 0.01

PARC = "Purchase Advance Receipt Control"
EXPECTED = "qty_to_be_received_against_the_advance_paid"


class PurchaseAdvanceReceiptControl(Document):
	pass


def _received_qty(purchase_order):
	"""Qty received to date against the PO across all submitted Purchase Receipts."""
	return flt(
		frappe.db.get_value(
			"Purchase Receipt Item", {"purchase_order": purchase_order, "docstatus": 1}, "sum(qty)"
		)
	)


def _draft_parcs(purchase_order):
	return frappe.get_all(
		PARC,
		filters={"purchase_order": purchase_order, "docstatus": 0},
		fields=["name", EXPECTED, "payment_entry", "advance_paid", "creation"],
		order_by="creation asc",
	)


def _best_match(parcs, qty):
	"""Draft PARC a receipt of `qty` would close: within tolerance, closest expected qty,
	ties to the oldest advance. None when nothing is within range."""
	tolerance = flt(qty) * MATCH_TOLERANCE
	matching = [p for p in parcs if abs(flt(p[EXPECTED]) - qty) <= tolerance]
	return min(matching, key=lambda p: (abs(flt(p[EXPECTED]) - qty), p["creation"])) if matching else None


def _qty_by_po(doc):
	"""Received qty per Purchase Order, summed across the receipt's item lines."""
	out = defaultdict(float)
	for item in doc.items:
		if item.purchase_order:
			out[item.purchase_order] += flt(item.qty)
	return out


# ---- Payment Entry: After Submit -> one draft PARC per Purchase Order reference ----------
def create_parc_on_payment_entry(doc, method=None):
	if doc.payment_type != "Pay" or doc.party_type != "Supplier":
		return
	for ref in doc.references:
		if ref.reference_doctype != "Purchase Order" or flt(ref.allocated_amount) <= 0:
			continue
		po = frappe.get_doc("Purchase Order", ref.reference_name)
		if not po.items:
			continue
		# ponytail: fuel POs carry one line; the original script read items[0] too. Loop the
		# lines (and apportion the advance) if multi-line POs ever need PARC.
		item = po.items[0]
		advance_pct = flt(ref.allocated_amount) / flt(po.grand_total) if flt(po.grand_total) > 0 else 0
		qty_adv = flt(item.qty) * advance_pct
		frappe.get_doc(
			{
				"doctype": PARC,
				"payment_entry": doc.name,
				"purchase_order": po.name,
				"qty_of_po": item.qty,
				"uom_of_item": item.uom,
				"rate_of_po": item.rate,
				"grand_total_of_po": po.grand_total,
				"advance_against_po__summary_": po.advance_paid,
				"advance_paid": ref.allocated_amount,
				EXPECTED: qty_adv,
				"qty_left_to_be_received_from_po": flt(item.qty) - qty_adv - _received_qty(po.name),
			}
		).insert(ignore_permissions=True)


# ---- Payment Entry: On Cancel -> drop the draft PARCs this advance opened ------------------
def delete_draft_parcs_on_payment_entry_cancel(doc, method=None):
	for name in frappe.get_all(PARC, filters={"payment_entry": doc.name, "docstatus": 0}, pluck="name"):
		frappe.delete_doc(PARC, name, ignore_permissions=True)


# ---- Purchase Receipt: Before Validate -> warn when this receipt will not close a PARC exactly
def warn_qty_mismatch_on_purchase_receipt(doc, method=None):
	for po, qty in _qty_by_po(doc).items():
		parcs = _draft_parcs(po)
		if not parcs:
			continue
		best = _best_match(parcs, qty)
		if best and abs(flt(best[EXPECTED]) - qty) <= QTY_EPSILON:
			continue
		frappe.msgprint(
			msg=_render_mismatch_warning(po, qty, parcs, best, doc.currency),
			title=_("Quantity Mismatch Warning"),
			indicator="orange",
		)


def _render_mismatch_warning(po, qty, parcs, best, currency):
	td = "border:1px solid #dee2e6;padding:8px;"
	rows = "".join(
		f"<tr><td style='{td}'><b>{p.name}</b></td>"
		f"<td style='{td}'>{format_datetime(p.creation, 'dd-MM-yyyy hh:mm:ss a')}</td>"
		f"<td style='{td}'>{p.payment_entry or 'N/A'}</td>"
		f"<td style='{td}text-align:right;'>{fmt_money(p.advance_paid, currency=currency)}</td>"
		f"<td style='{td}text-align:right;'>{flt(p[EXPECTED]):.2f}</td></tr>"
		for p in parcs
	)
	if best:
		verdict = (
			f"<b style='color:#0066cc;'>Closest PARC: {best.name} (expected {flt(best[EXPECTED]):.2f})</b><br>"
			f"<b style='color:#dc3545;'>Difference: {qty - flt(best[EXPECTED]):.2f}</b><br>"
		)
	else:
		verdict = f"<b style='color:#dc3545;'>No draft PARC within &plusmn;{MATCH_TOLERANCE:.0%} of this quantity; none will be closed.</b><br>"
	return f"""
	<b>&#9888; Purchase Order: {po}</b><br><br>
	<b>Purchase Receipt Quantity: {qty:.2f}</b><br><br>
	<b>Related PARC Records (Draft Only):</b><br>
	<table style='width:100%;border-collapse:collapse;margin-top:10px;'>
	<tr style='background-color:#f8f9fa;'>
	<th style='{td}text-align:left;'>PARC Number</th><th style='{td}text-align:left;'>Date &amp; Time</th>
	<th style='{td}text-align:left;'>Payment Entry</th><th style='{td}text-align:right;'>Payment Amount</th>
	<th style='{td}text-align:right;'>Expected Qty</th></tr>{rows}</table><br>
	{verdict}<br>
	<i>You can still submit this Purchase Receipt.</i>
	"""


# ---- Purchase Receipt: After Submit -> close the best-matching draft PARC ------------------
def close_parc_on_purchase_receipt(doc, method=None):
	for po, qty in _qty_by_po(doc).items():
		parcs = _draft_parcs(po)
		if not parcs:
			continue
		best = _best_match(parcs, qty)
		if not best:
			tolerance = qty * MATCH_TOLERANCE
			frappe.msgprint(
				_("No PARC found within &plusmn;20% range for PO: {0}<br>Receipt Qty: {1:.2f} (Range: {2:.2f} - {3:.2f})").format(
					po, qty, qty - tolerance, qty + tolerance
				),
				alert=True,
				indicator="orange",
			)
			continue
		try:
			parc = frappe.get_doc(PARC, best.name)
			parc.purchase_receipt = doc.name
			parc.qty_of_pr = qty
			parc.grand_total_of_pr = doc.grand_total
			# Received-to-date already includes this receipt (docstatus is 1 by on_submit).
			parc.qty_left_to_be_received_from_po = flt(parc.qty_of_po) - _received_qty(po)
			parc.flags.ignore_permissions = True
			parc.submit()  # one save: no half-updated draft left behind if submit fails
			frappe.msgprint(
				_("PARC {0} updated and submitted<br>PO: {1}<br>Expected Qty: {2:.2f}, Actual Qty: {3:.2f}").format(
					best.name, po, flt(best[EXPECTED]), qty
				),
				alert=True,
				indicator="green",
			)
		except Exception as e:
			# As before: a PARC that will not submit must not block the Purchase Receipt.
			frappe.msgprint(_("Error submitting PARC: {0}").format(e), alert=True, indicator="red")
			frappe.log_error(f"PARC Submit Error: {e}", "PARC Submission Failed")


# ---- Purchase Receipt: On Cancel -> cancel the closed PARC and re-open the advance ---------
def reopen_parc_on_purchase_receipt_cancel(doc, method=None):
	# Runs before Frappe's back-link check, so cancelling the PARC here is what lets the
	# Purchase Receipt cancel at all.
	for name in frappe.get_all(PARC, filters={"purchase_receipt": doc.name, "docstatus": 1}, pluck="name"):
		parc = frappe.get_doc(PARC, name)
		parc.flags.ignore_permissions = True
		parc.cancel()
		draft = frappe.copy_doc(parc)
		draft.docstatus = 0  # copy_doc keeps the source's (now cancelled) docstatus
		draft.purchase_receipt = None
		draft.qty_of_pr = None
		draft.grand_total_of_pr = None
		draft.qty_left_to_be_received_from_po = (
			flt(parc.qty_of_po) - flt(parc.get(EXPECTED)) - _received_qty(parc.purchase_order)
		)
		draft.insert(ignore_permissions=True)

// Client Script | Purchase Receipt | Form | "Purchase Advance Receipt Control - PR Dashboard"
// Shows, before save, which draft PARC advances exist for the POs on this receipt and what each
// expects, so the user knows what the submit will close. After submit, links the PARC it closed.
const PARC = "Purchase Advance Receipt Control";
const EXP = "qty_to_be_received_against_the_advance_paid";

function parc_pos(frm) {
	return [...new Set((frm.doc.items || []).map((d) => d.purchase_order).filter(Boolean))];
}

async function show_parcs(frm) {
	frm.dashboard.clear_headline();
	const pos = parc_pos(frm);
	if (!pos.length) return;

	if (frm.doc.docstatus === 1) {
		const closed = await frappe.db.get_list(PARC, {
			filters: { purchase_receipt: frm.doc.name, docstatus: 1 },
			fields: ["name", "purchase_order", "qty_of_pr"],
		});
		if (closed.length) {
			const links = closed.map((p) => `${frappe.utils.get_form_link(PARC, p.name, true)} (${p.purchase_order})`);
			frm.dashboard.set_headline_alert(__("Closed PARC: {0}", [links.join(", ")]), "green");
		}
		return;
	}

	const drafts = await frappe.db.get_list(PARC, {
		filters: { purchase_order: ["in", pos], docstatus: 0 },
		fields: ["name", "purchase_order", EXP, "payment_entry"],
		order_by: "creation asc",
		limit: 50,
	});
	if (!drafts.length) return;

	const qty_by_po = {};
	(frm.doc.items || []).forEach((d) => {
		if (d.purchase_order) qty_by_po[d.purchase_order] = (qty_by_po[d.purchase_order] || 0) + flt(d.qty);
	});
	const lines = pos
		.filter((po) => drafts.some((p) => p.purchase_order === po))
		.map((po) => {
			const expected = drafts
				.filter((p) => p.purchase_order === po)
				.map((p) => `${frappe.utils.get_form_link(PARC, p.name, true)} expects ${format_number(p[EXP], null, 2)}`);
			return __("{0}: this receipt {1} · pending advances: {2}", [
				po, format_number(qty_by_po[po] || 0, null, 2), expected.join(", "),
			]);
		});
	frm.dashboard.set_headline_alert(lines.join("<br>"), "orange");
}

frappe.ui.form.on("Purchase Receipt", {
	refresh(frm) {
		show_parcs(frm);
		if (parc_pos(frm).length) {
			frm.add_custom_button(__("PARC"), () => {
				frappe.set_route("List", PARC, { purchase_order: ["in", parc_pos(frm)] });
			}, __("View"));
		}
	},
});

frappe.ui.form.on("Purchase Receipt Item", {
	purchase_order(frm) { show_parcs(frm); },
	qty(frm) { show_parcs(frm); },
	items_remove(frm) { show_parcs(frm); },
});

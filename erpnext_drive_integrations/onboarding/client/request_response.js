// "Request response" button (ADR-039) on Purchase Order and Job Offer, loaded through hooks.doctype_js
// (read from disk with the form; no asset build). Shown only when a Response Rule is enabled for the doctype
// and the user's role may request. The server re-checks everything.
if (!window.hov_request_response_loaded) {
	window.hov_request_response_loaded = true;
	const rule_cache = {};
	const recipient = (frm) =>
		frm.doctype === "Job Offer"
			? { name: frm.doc.applicant_name, email: frm.doc.applicant_email }
			: { name: frm.doc.supplier_name || frm.doc.supplier, email: frm.doc.contact_email };

	const refresh = (frm) => {
		if (frm.is_new() || frm.doc.docstatus === 2) return;
		const status = rule_cache[frm.doctype] || (rule_cache[frm.doctype] = frappe.xcall("erpnext_drive_integrations.onboarding.respond.rule_status", { doctype: frm.doctype }, "GET"));
		status.then((s) => {
			if (!s.enabled || !s.can_request) return;
			frm.add_custom_button(__("Request response"), () => {
				const r = recipient(frm);
				frappe.prompt(
					[
						{ fieldname: "recipient_name", fieldtype: "Data", label: __("Name"), default: r.name, reqd: 1 },
						{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("Email"), default: r.email, reqd: 1 },
					],
					(v) =>
						frappe
							.xcall("erpnext_drive_integrations.onboarding.respond.request_document_response", { doctype: frm.doctype, name: frm.doc.name, ...v })
							.then((res) => {
								frappe.msgprint({
									title: __("Sent by email. Hand-share link (shown only once):"),
									message: `<input class="form-control" readonly value="${frappe.utils.escape_html(res.manual_link)}">`,
								});
								frm.reload_doc();
							}),
					__("Send for accept / reject"),
					__("Send")
				);
			});
		});
	};
	["Purchase Order", "Job Offer"].forEach((dt) => frappe.ui.form.on(dt, { refresh }));
}

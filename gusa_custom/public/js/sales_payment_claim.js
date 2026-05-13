frappe.ui.form.on("Sales Payment Claim", {
  refresh(frm) {
    add_accounting_buttons(frm);
    show_claim_indicators(frm);
  },
  sales_order(frm) {
    if (!frm.doc.sales_order) return;
    frappe.db.get_value("Sales Order", frm.doc.sales_order, ["customer", "company"], (r) => {
      if (!r) return;
      if (r.customer) frm.set_value("customer", r.customer);
      if (r.company) frm.set_value("company", r.company);
    });
  },
});

function is_accounting_user() {
  return frappe.user.has_role("Accounts User") ||
    frappe.user.has_role("Accounts Manager") ||
    frappe.user.has_role("System Manager");
}

function add_accounting_buttons(frm) {
  if (!is_accounting_user() || frm.is_new()) return;

  if (frm.doc.payment_entry) {
    frm.add_custom_button(__("Mở Payment Entry"), () => {
      frappe.set_route("Form", "Payment Entry", frm.doc.payment_entry);
    }, __("Kế toán"));
    return;
  }

  if (frm.doc.status === "Đã xác nhận" || frm.doc.status === "Thừa tiền") {
    frm.add_custom_button(__("Tạo Payment Entry nháp"), () => {
      frappe.call({
        method: "gusa_custom.sales_payment_claim.make_payment_entry_from_claim",
        args: { claim_name: frm.doc.name },
        freeze: true,
        callback(r) {
          if (r.message) frappe.set_route("Form", "Payment Entry", r.message);
        },
      });
    }, __("Kế toán"));
  }
}

function show_claim_indicators(frm) {
  const currency = frappe.defaults.get_default("currency") || "VND";
  if (frm.doc.status === "Thiếu tiền") {
    frm.dashboard.set_headline_alert(
      __("Còn phải xử lý: {0}", [format_currency(frm.doc.remaining_claim_amount || 0, currency)]),
      "orange",
    );
  } else if (frm.doc.status === "Thừa tiền") {
    frm.dashboard.set_headline_alert(
      __("Khách chuyển thừa: {0}", [format_currency(Math.abs(frm.doc.difference_amount || 0), currency)]),
      "blue",
    );
  } else if (frm.doc.status === "Đã xác nhận" && !frm.doc.payment_entry) {
    frm.dashboard.set_headline_alert(__("Đã xác nhận tiền nhưng chưa tạo Payment Entry"), "yellow");
  }
}

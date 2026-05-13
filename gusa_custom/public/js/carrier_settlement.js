frappe.ui.form.on("Carrier Settlement", {
  refresh(frm) {
    calculate_totals(frm);
  },
  validate(frm) {
    calculate_totals(frm);
  },
});

frappe.ui.form.on("Carrier Settlement Line", {
  cod_amount(frm, cdt, cdn) {
    calculate_line(frm, cdt, cdn);
  },
  shipping_fee(frm, cdt, cdn) {
    calculate_line(frm, cdt, cdn);
  },
  return_fee(frm, cdt, cdn) {
    calculate_line(frm, cdt, cdn);
  },
  actual_received(frm, cdt, cdn) {
    calculate_line(frm, cdt, cdn);
  },
  items_add(frm) {
    calculate_totals(frm);
  },
  items_remove(frm) {
    calculate_totals(frm);
  },
});

function calculate_line(frm, cdt, cdn) {
  const row = locals[cdt][cdn];
  const expected = flt(row.cod_amount) - flt(row.shipping_fee) - flt(row.return_fee);
  const difference = flt(row.actual_received) - expected;
  frappe.model.set_value(cdt, cdn, "difference_amount", difference);
  if (!row.line_status || ["Matched", "Difference"].includes(row.line_status)) {
    frappe.model.set_value(cdt, cdn, "line_status", difference === 0 ? "Matched" : "Difference");
  }
  calculate_totals(frm);
}

function calculate_totals(frm) {
  let cod = 0;
  let shipping = 0;
  let returns = 0;
  let received = 0;
  let difference = 0;

  (frm.doc.items || []).forEach((row) => {
    cod += flt(row.cod_amount);
    shipping += flt(row.shipping_fee);
    returns += flt(row.return_fee);
    received += flt(row.actual_received);
    difference += flt(row.difference_amount);
  });

  frm.set_value("total_cod_amount", cod);
  frm.set_value("total_shipping_fee", shipping);
  frm.set_value("total_return_fee", returns);
  frm.set_value("total_actual_received", received);
  frm.set_value("total_difference_amount", difference);
}

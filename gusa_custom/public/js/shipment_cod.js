frappe.ui.form.on("Shipment", {
  custom_cod_amount(frm) {
    frm.set_value("custom_cod_required", flt(frm.doc.custom_cod_amount) > 0 ? 1 : 0);
  },
  validate(frm) {
    if (flt(frm.doc.custom_cod_amount) > 0 && !frm.doc.custom_cod_required) {
      frm.set_value("custom_cod_required", 1);
    }
  },
});

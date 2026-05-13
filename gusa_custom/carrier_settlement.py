import frappe
from frappe import _
from frappe.utils import flt


OPEN_STATUSES = {"Draft", "Checking", "Difference", None, ""}
FINAL_STATUSES = {"Confirmed", "Paid", "Cancelled"}


def validate_carrier_settlement(doc, method=None):
    calculate_carrier_settlement(doc)
    validate_duplicate_shipments(doc)


def before_submit_carrier_settlement(doc, method=None):
    calculate_carrier_settlement(doc)
    if flt(doc.total_difference_amount) != 0:
        if not doc.get("difference_approved"):
            doc.status = "Difference"
            frappe.throw(_("Bảng kê còn chênh lệch. Accounts Manager phải duyệt lệch trước khi submit."))
        if not any(frappe.has_role(role) for role in ("Accounts Manager", "System Manager")):
            frappe.throw(_("Chỉ Accounts Manager/System Manager được submit bảng kê có chênh lệch đã duyệt."))
        if not doc.get("difference_approval_note"):
            frappe.throw(_("Cần ghi lý do duyệt chênh lệch."))
    doc.status = "Confirmed"


def calculate_carrier_settlement(doc):
    total_cod = 0
    total_shipping = 0
    total_return = 0
    total_received = 0
    total_difference = 0

    for row in doc.get("items", []):
        hydrate_settlement_line(row)
        expected = flt(row.cod_amount) - flt(row.shipping_fee) - flt(row.return_fee)
        row.difference_amount = flt(row.actual_received) - expected

        if not row.line_status or row.line_status in {"Matched", "Difference"}:
            row.line_status = "Matched" if row.difference_amount == 0 else "Difference"

        total_cod += flt(row.cod_amount)
        total_shipping += flt(row.shipping_fee)
        total_return += flt(row.return_fee)
        total_received += flt(row.actual_received)
        total_difference += flt(row.difference_amount)

    doc.total_cod_amount = total_cod
    doc.total_shipping_fee = total_shipping
    doc.total_return_fee = total_return
    doc.total_actual_received = total_received
    doc.total_difference_amount = total_difference

    if doc.status in OPEN_STATUSES:
        doc.status = "Difference" if total_difference else "Checking"


def hydrate_settlement_line(row):
    if not row.shipment:
        return

    shipment = frappe.get_doc("Shipment", row.shipment)
    row.awb_number = row.awb_number or shipment.get("awb_number")
    row.customer = row.customer or shipment.get("delivery_customer")
    if flt(row.cod_amount) == 0:
        row.cod_amount = flt(shipment.get("custom_cod_amount"))


def validate_duplicate_shipments(doc):
    seen = set()
    for row in doc.get("items", []):
        if not row.shipment:
            continue
        if row.shipment in seen:
            frappe.throw(_("Shipment {0} bị lặp trong cùng bảng kê.").format(row.shipment))
        seen.add(row.shipment)

        existing = frappe.db.sql(
            """
            select parent
            from `tabCarrier Settlement Line`
            where shipment = %s
              and parent != %s
              and parenttype = 'Carrier Settlement'
              and docstatus < 2
            limit 1
            """,
            (row.shipment, doc.name or ""),
            as_dict=True,
        )
        if existing:
            frappe.throw(
                _("Shipment {0} đã nằm trong bảng kê {1}.").format(
                    row.shipment, existing[0].parent
                )
            )


@frappe.whitelist()
def import_carrier_settlement_rows(settlement_name, rows):
    doc = frappe.get_doc("Carrier Settlement", settlement_name)
    doc.check_permission("write")

    for data in rows:
        row = doc.append("items", {})
        row.shipment = data.get("shipment")
        row.awb_number = data.get("awb_number")
        row.customer = data.get("customer")
        row.cod_amount = flt(data.get("cod_amount"))
        row.shipping_fee = flt(data.get("shipping_fee"))
        row.return_fee = flt(data.get("return_fee"))
        row.actual_received = flt(data.get("actual_received"))
        row.note = data.get("note")

    calculate_carrier_settlement(doc)
    doc.save()
    return doc.name

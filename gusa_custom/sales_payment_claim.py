import frappe
from frappe import _
from frappe.utils import flt, now_datetime


ACCOUNTING_FIELDS = {
    "verified_amount",
    "difference_amount",
    "remaining_claim_amount",
    "payment_entry",
    "verified_by",
    "verified_at",
    "accounting_note",
}

FINAL_STATUSES = {"Đã tạo Payment Entry", "Từ chối", "Đã hủy"}
VERIFIED_STATUSES = {"Đã xác nhận", "Thiếu tiền", "Thừa tiền"}


def is_accounts_user() -> bool:
    return any(
        frappe.has_role(role)
        for role in ("Accounts User", "Accounts Manager", "System Manager")
    )


def is_accounts_manager() -> bool:
    return any(frappe.has_role(role) for role in ("Accounts Manager", "System Manager"))


def before_save_payment_claim(doc, method=None):
    hydrate_sales_order_fields(doc)
    assert_accounting_field_access(doc)
    assert_booked_claim_locked(doc)
    compute_payment_claim(doc)


def validate_payment_claim(doc, method=None):
    if flt(doc.claimed_amount) <= 0:
        frappe.throw(_("Số tiền khách báo phải lớn hơn 0."))

    if doc.sales_order:
        so = frappe.get_doc("Sales Order", doc.sales_order)
        if doc.customer and doc.customer != so.customer:
            frappe.throw(_("Khách hàng trên claim không khớp với Đơn bán hàng."))
        if doc.company and doc.company != so.company:
            frappe.throw(_("Công ty trên claim không khớp với Đơn bán hàng."))

    if doc.payment_entry:
        validate_payment_entry_matches_claim(doc.payment_entry, doc)


def hydrate_sales_order_fields(doc):
    if not doc.sales_order:
        return

    so = frappe.get_doc("Sales Order", doc.sales_order)
    doc.customer = so.customer
    doc.company = so.company


def assert_accounting_field_access(doc):
    if doc.is_new() or is_accounts_user():
        return

    old = doc.get_doc_before_save()
    if not old:
        return

    changed = [
        fieldname
        for fieldname in ACCOUNTING_FIELDS
        if doc.get(fieldname) != old.get(fieldname)
    ]
    if changed:
        frappe.throw(_("Sale không được sửa vùng Kế toán xử lý."))


def assert_booked_claim_locked(doc):
    if frappe.flags.in_payment_entry_claim_sync:
        return

    if is_accounts_manager():
        return

    old = doc.get_doc_before_save()
    was_booked = bool(old and (old.payment_entry or old.status == "Đã tạo Payment Entry"))
    is_booked = bool(doc.payment_entry or doc.status == "Đã tạo Payment Entry")
    if was_booked or is_booked:
        frappe.throw(_("Claim đã có Payment Entry. Chỉ Accounts Manager/System Manager được sửa."))


def compute_payment_claim(doc):
    if not doc.status or doc.status == "Draft":
        doc.status = "Chờ kế toán kiểm tra"

    claimed = flt(doc.claimed_amount)
    verified = flt(doc.verified_amount)
    has_verified = verified > 0

    doc.difference_amount = verified - claimed if has_verified else 0
    doc.remaining_claim_amount = max(claimed - verified, 0) if has_verified else claimed

    if doc.payment_entry:
        doc.status = "Đã tạo Payment Entry"
        return

    if has_verified and doc.status not in FINAL_STATUSES:
        if doc.difference_amount == 0:
            doc.status = "Đã xác nhận"
        elif doc.difference_amount < 0:
            doc.status = "Thiếu tiền"
        else:
            doc.status = "Thừa tiền"

    if doc.status in VERIFIED_STATUSES:
        doc.verified_by = doc.verified_by or frappe.session.user
        doc.verified_at = doc.verified_at or now_datetime()


@frappe.whitelist()
def make_payment_entry_from_claim(claim_name):
    claim = frappe.get_doc("Sales Payment Claim", claim_name)
    claim.check_permission("write")

    if not is_accounts_user():
        frappe.throw(_("Chỉ kế toán được tạo Payment Entry từ claim."))

    compute_payment_claim(claim)
    if claim.status not in {"Đã xác nhận", "Thừa tiền"}:
        frappe.throw(_("Chỉ tạo Payment Entry khi claim đã xác nhận tiền thực nhận."))

    if claim.payment_entry:
        return claim.payment_entry

    verified_amount = flt(claim.verified_amount)
    if verified_amount <= 0:
        frappe.throw(_("Số tiền thực nhận phải lớn hơn 0."))

    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = "Receive"
    pe.company = claim.company
    pe.party_type = "Customer"
    pe.party = claim.customer
    pe.mode_of_payment = claim.mode_of_payment
    pe.paid_amount = verified_amount
    pe.received_amount = verified_amount
    pe.reference_no = claim.transfer_reference or claim.name
    pe.reference_date = claim.claim_date
    pe.remarks = _("Created from Sales Payment Claim {0}").format(claim.name)

    set_payment_entry_accounts(pe, claim)
    add_payment_reference(pe, claim, verified_amount)

    if frappe.get_meta("Payment Entry").has_field("gusa_sales_payment_claim"):
        pe.gusa_sales_payment_claim = claim.name

    pe.insert(ignore_permissions=False)
    return pe.name


def set_payment_entry_accounts(pe, claim):
    settings = get_operations_settings(claim.company)

    pe.paid_from = settings.get("receivable_account") or get_party_receivable_account(
        claim.company, claim.customer
    )
    pe.paid_to = get_paid_to_account(settings, claim.mode_of_payment)

    if not pe.paid_to:
        frappe.throw(_("Chưa cấu hình tài khoản nhận tiền cho phương thức {0}.").format(claim.mode_of_payment))


def get_paid_to_account(settings, mode_of_payment):
    account = get_mode_of_payment_default_account(mode_of_payment)
    if account:
        return account

    if mode_of_payment == "Tiền mặt":
        return settings.get("cash_account")
    if mode_of_payment == "COD":
        return settings.get("cod_clearing_account") or settings.get("bank_account")
    return settings.get("bank_account")


def get_mode_of_payment_default_account(mode_of_payment):
    if not mode_of_payment or not frappe.db.exists("DocType", "Mode of Payment Account"):
        return None

    account = frappe.db.get_value(
        "Mode of Payment Account",
        {"parent": mode_of_payment, "company": frappe.defaults.get_user_default("Company")},
        "default_account",
    )
    if account:
        return account

    return frappe.db.get_value(
        "Mode of Payment Account",
        {"parent": mode_of_payment},
        "default_account",
    )


def get_party_receivable_account(company, customer):
    from erpnext.accounts.party import get_party_account

    return get_party_account("Customer", customer, company)


def add_payment_reference(pe, claim, amount):
    invoice = get_best_unpaid_sales_invoice(claim.sales_order, claim.customer)
    row = pe.append("references", {})

    if invoice:
        outstanding = flt(invoice.outstanding_amount)
        row.reference_doctype = "Sales Invoice"
        row.reference_name = invoice.name
        row.allocated_amount = min(amount, outstanding) if outstanding > 0 else amount
        return

    row.reference_doctype = "Sales Order"
    row.reference_name = claim.sales_order
    row.allocated_amount = amount


def get_best_unpaid_sales_invoice(sales_order, customer):
    rows = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "customer": customer,
            "outstanding_amount": [">", 0],
        },
        fields=["name", "outstanding_amount", "posting_date", "modified"],
        order_by="posting_date asc, modified asc",
        limit=20,
    )

    for row in rows:
        if frappe.db.exists(
            "Sales Invoice Item",
            {"parent": row.name, "sales_order": sales_order},
        ):
            return row
    return None


def validate_payment_entry(doc, method=None):
    claim_name = doc.get("gusa_sales_payment_claim")
    if not claim_name:
        return

    claim = frappe.get_doc("Sales Payment Claim", claim_name)
    validate_payment_entry_matches_claim(doc, claim)


def validate_payment_entry_matches_claim(payment_entry, claim):
    pe = (
        frappe.get_doc("Payment Entry", payment_entry)
        if isinstance(payment_entry, str)
        else payment_entry
    )

    if pe.payment_type != "Receive":
        frappe.throw(_("Payment Entry từ claim phải là Receive."))
    if pe.company != claim.company:
        frappe.throw(_("Payment Entry không khớp công ty của claim."))
    if pe.party_type != "Customer" or pe.party != claim.customer:
        frappe.throw(_("Payment Entry không khớp khách hàng của claim."))
    if flt(pe.received_amount) <= 0:
        frappe.throw(_("Payment Entry phải có số tiền thực nhận lớn hơn 0."))
    if flt(pe.received_amount) > flt(claim.verified_amount) and not is_accounts_manager():
        frappe.throw(_("Payment Entry vượt số tiền kế toán xác nhận trên claim."))

    validate_payment_entry_references(pe, claim)


def validate_payment_entry_references(pe, claim):
    references = pe.get("references") or []
    if not references:
        return

    for row in references:
        if row.reference_doctype == "Sales Order":
            if row.reference_name != claim.sales_order:
                frappe.throw(_("Payment Entry đang phân bổ vào Sales Order khác claim."))
            continue

        if row.reference_doctype == "Sales Invoice":
            if not sales_invoice_belongs_to_order(row.reference_name, claim.sales_order):
                frappe.throw(_("Payment Entry đang phân bổ vào Sales Invoice không thuộc Đơn bán hàng của claim."))
            continue

        frappe.throw(_("Payment Entry từ claim chỉ được phân bổ vào Sales Invoice hoặc Sales Order."))


def sales_invoice_belongs_to_order(sales_invoice, sales_order):
    return frappe.db.exists(
        "Sales Invoice Item",
        {"parent": sales_invoice, "sales_order": sales_order},
    )


def on_payment_entry_submit(doc, method=None):
    claim_name = doc.get("gusa_sales_payment_claim")
    if not claim_name:
        return

    claim = frappe.get_doc("Sales Payment Claim", claim_name)
    claim.payment_entry = doc.name
    claim.status = "Đã tạo Payment Entry"
    frappe.flags.in_payment_entry_claim_sync = True
    try:
        claim.save(ignore_permissions=True)
    finally:
        frappe.flags.in_payment_entry_claim_sync = False


def on_payment_entry_cancel(doc, method=None):
    claim_name = doc.get("gusa_sales_payment_claim")
    if not claim_name:
        return

    claim = frappe.get_doc("Sales Payment Claim", claim_name)
    if claim.payment_entry == doc.name:
        claim.payment_entry = None
    compute_payment_claim(claim)
    frappe.flags.in_payment_entry_claim_sync = True
    try:
        claim.save(ignore_permissions=True)
    finally:
        frappe.flags.in_payment_entry_claim_sync = False


def get_operations_settings(company=None):
    if not frappe.db.exists("DocType", "GUSA Operations Settings"):
        return {}

    settings = frappe.get_single("GUSA Operations Settings")
    return {
        "bank_account": settings.get("bank_account"),
        "cash_account": settings.get("cash_account"),
        "receivable_account": settings.get("receivable_account"),
        "cod_clearing_account": settings.get("cod_clearing_account"),
        "shipping_fee_expense_account": settings.get("shipping_fee_expense_account"),
        "difference_account": settings.get("difference_account"),
    }

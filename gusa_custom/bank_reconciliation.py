import re

import frappe
from frappe import _
from frappe.utils import flt, getdate


def normalize_reference(value):
    value = (value or "").upper()
    return re.sub(r"[^A-Z0-9]", "", value)


@frappe.whitelist()
def suggest_bank_matches(transaction_name):
    txn = frappe.get_doc("Bank Statement Transaction", transaction_name)
    txn.check_permission("read")

    amount = flt(txn.amount)
    if amount <= 0:
        return []

    normalized_description = normalize_reference(txn.description)
    candidates = []

    claims = frappe.get_all(
        "Sales Payment Claim",
        filters={
            "docstatus": ["<", 2],
            "payment_entry": ["is", "not set"],
            "status": ["in", ["Chờ kế toán kiểm tra", "Đã xác nhận", "Thiếu tiền", "Thừa tiền"]],
        },
        fields=[
            "name",
            "sales_order",
            "customer",
            "claim_date",
            "claimed_amount",
            "verified_amount",
            "transfer_reference",
            "status",
        ],
        limit=200,
    )

    for claim in claims:
        score = 0
        claim_amount = flt(claim.verified_amount) or flt(claim.claimed_amount)
        if claim_amount == amount:
            score += 50
        elif abs(claim_amount - amount) <= 1000:
            score += 25

        ref = normalize_reference(claim.transfer_reference or claim.sales_order or claim.name)
        if ref and ref in normalized_description:
            score += 40

        if claim.claim_date and txn.transaction_date:
            days = abs((getdate(txn.transaction_date) - getdate(claim.claim_date)).days)
            if days == 0:
                score += 10
            elif days <= 3:
                score += 5

        if score:
            candidates.append({**claim, "score": score})

    return sorted(candidates, key=lambda item: item["score"], reverse=True)


@frappe.whitelist()
def allocate_bank_transaction(transaction_name, claim_name, amount=None):
    txn = frappe.get_doc("Bank Statement Transaction", transaction_name)
    claim = frappe.get_doc("Sales Payment Claim", claim_name)
    txn.check_permission("write")
    claim.check_permission("write")

    allocation_amount = flt(amount) or flt(txn.amount)
    if allocation_amount <= 0:
        frappe.throw(_("Số tiền phân bổ phải lớn hơn 0."))

    existing_total = sum(flt(row.allocated_amount) for row in txn.get("allocations", []))
    if existing_total + allocation_amount > flt(txn.amount):
        frappe.throw(_("Tổng phân bổ vượt số tiền giao dịch ngân hàng."))

    if any(row.sales_payment_claim == claim.name for row in txn.get("allocations", [])):
        frappe.throw(_("Claim này đã được phân bổ trong giao dịch ngân hàng."))

    row = txn.append("allocations", {})
    row.sales_payment_claim = claim.name
    row.allocated_amount = allocation_amount
    row.customer = claim.customer
    row.sales_order = claim.sales_order
    txn.match_status = "Matched" if existing_total + allocation_amount == flt(txn.amount) else "Suggested"
    txn.save()
    return txn.name

app_name = "gusa_custom"
app_title = "GUSA Custom"
app_publisher = "GUSA Vietnam"
app_description = "Vietnam operations customizations for ERPNext"
app_email = "admin@gusavietnam.vn"
app_license = "MIT"
frappe_version = ">=16.0.0 <17.0.0"
erpnext_version = ">=16.0.0 <17.0.0"

after_install = "gusa_custom.install.after_install"
after_migrate = "gusa_custom.install.after_migrate"

doc_events = {
    "Sales Payment Claim": {
        "validate": "gusa_custom.sales_payment_claim.validate_payment_claim",
        "before_save": "gusa_custom.sales_payment_claim.before_save_payment_claim",
    },
    "Payment Entry": {
        "validate": "gusa_custom.sales_payment_claim.validate_payment_entry",
        "on_submit": "gusa_custom.sales_payment_claim.on_payment_entry_submit",
        "on_cancel": "gusa_custom.sales_payment_claim.on_payment_entry_cancel",
    },
    "Carrier Settlement": {
        "validate": "gusa_custom.carrier_settlement.validate_carrier_settlement",
        "before_submit": "gusa_custom.carrier_settlement.before_submit_carrier_settlement",
    },
}

doctype_js = {
    "Sales Payment Claim": "public/js/sales_payment_claim.js",
    "Carrier Settlement": "public/js/carrier_settlement.js",
    "Shipment": "public/js/shipment_cod.js",
}

fixtures = [
    {"dt": "Custom Field", "filters": [["name", "like", "Shipment-custom_%"]]},
    {"dt": "Custom Field", "filters": [["name", "like", "Payment Entry-gusa_%"]]},
    {"dt": "Report", "filters": [["name", "in", [
        "Sales Payment Claims Pending",
        "Sales Payment Claims Summary",
        "Sales Payment Claims by Sales Order",
        "Sales Payment Claims Confirmed Not Booked",
        "Shipment Operations View",
        "COD Pending Cash",
        "COD Settlement Dashboard",
        "Carrier Receivables",
    ]]]},
    {"dt": "Mode of Payment", "filters": [["name", "in", ["Chuyển khoản", "Tiền mặt", "COD", "QR"]]]},
    {"dt": "Payment Terms Template", "filters": [["name", "in", [
        "Thanh toán 100% trước",
        "Cọc 30% - còn lại trước giao",
        "Cọc 50% - còn lại khi giao",
        "COD",
        "Công nợ 7 ngày",
        "Công nợ 15 ngày",
        "Công nợ 30 ngày",
    ]]]},
]

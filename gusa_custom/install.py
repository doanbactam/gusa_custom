import frappe


def after_install():
    after_migrate()


def after_migrate():
    ensure_modules()
    ensure_custom_fields()
    ensure_reports()
    ensure_workspace()
    frappe.db.commit()


def ensure_modules():
    if not frappe.db.exists("Module Def", "GUSA Custom"):
        frappe.get_doc(
            {
                "doctype": "Module Def",
                "module_name": "GUSA Custom",
                "app_name": "gusa_custom",
                "custom": 0,
            }
        ).insert(ignore_permissions=True)


def ensure_custom_fields():
    custom_fields = [
        ("Shipment", "custom_vn_ops_section", "Vận hành Việt Nam", "Section Break", None, "tracking_status_info"),
        ("Shipment", "custom_sales_channel", "Kênh bán", "Select", "Website\nSàn TMĐT\nPOS\nKhác", "custom_vn_ops_section"),
        ("Shipment", "custom_fulfillment_method", "Phương thức giao hàng", "Select", "Tự giao\nĐơn vị vận chuyển\nSàn giao\nKhác", "custom_sales_channel"),
        ("Shipment", "custom_cod_required", "Có COD", "Check", None, "custom_fulfillment_method"),
        ("Shipment", "custom_cod_amount", "Số COD cần thu", "Currency", None, "custom_cod_required"),
        ("Payment Entry", "gusa_sales_payment_claim", "Sales Payment Claim", "Link", "Sales Payment Claim", "remarks"),
    ]

    for dt, fieldname, label, fieldtype, options, insert_after in custom_fields:
        name = f"{dt}-{fieldname}"
        if frappe.db.exists("Custom Field", name):
            continue
        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": dt,
                "fieldname": fieldname,
                "label": label,
                "fieldtype": fieldtype,
                "options": options,
                "insert_after": insert_after,
            }
        ).insert(ignore_permissions=True)


def ensure_reports():
    reports = {
        "Sales Payment Claims Confirmed Not Booked": """
select name as "Claim:Link/Sales Payment Claim:160", sales_order as "Đơn bán hàng:Link/Sales Order:160",
customer as "Khách hàng:Link/Customer:150", claim_date as "Ngày báo:Date:110",
mode_of_payment as "Phương thức:Link/Mode of Payment:130", claimed_amount as "Khách báo:Currency:120",
verified_amount as "Đã xác nhận:Currency:130", transfer_reference as "Mã/Nội dung GD:Data:180",
verified_by as "Kế toán xác nhận:Link/User:150", verified_at as "Thời điểm xác nhận:Datetime:160"
from `tabSales Payment Claim`
where docstatus < 2 and status = 'Đã xác nhận' and ifnull(payment_entry, '') = ''
order by verified_at desc, modified desc
""",
        "Sales Payment Claims Summary": """
select status as "Trạng thái:Data:160", count(name) as "Số claim:Int:100",
sum(ifnull(claimed_amount, 0)) as "Tổng khách báo:Currency:150",
sum(ifnull(verified_amount, 0)) as "Tổng thực nhận:Currency:150",
sum(ifnull(remaining_claim_amount, 0)) as "Tổng còn xử lý:Currency:150",
sum(ifnull(difference_amount, 0)) as "Tổng lệch:Currency:130"
from `tabSales Payment Claim`
where docstatus < 2
group by status
""",
        "COD Pending Cash": """
select s.name as "Shipment:Link/Shipment:150", s.awb_number as "Mã vận đơn:Data:140",
s.carrier as "Carrier:Data:140", s.custom_cod_amount as "Số COD:Currency:120",
s.tracking_status as "Tracking:Data:120", coalesce(csl.parent, '') as "Bảng kê:Link/Carrier Settlement:150"
from `tabShipment` s
left join `tabCarrier Settlement Line` csl on csl.shipment = s.name
where ifnull(s.custom_cod_required, 0) = 1 and ifnull(s.custom_cod_amount, 0) > 0
""",
    }
    for name, query in reports.items():
        if frappe.db.exists("Report", name):
            continue
        frappe.get_doc(
            {
                "doctype": "Report",
                "report_name": name,
                "name": name,
                "ref_doctype": "Sales Payment Claim" if name.startswith("Sales") else "Shipment",
                "report_type": "Query Report",
                "is_standard": "No",
                "query": query.strip(),
            }
        ).insert(ignore_permissions=True)


def ensure_workspace():
    links = [
        {"type": "Card Break", "label": "Thanh toán bán hàng"},
        {
            "type": "Link",
            "label": "Yêu cầu ghi nhận thanh toán",
            "link_type": "DocType",
            "link_to": "Sales Payment Claim",
            "onboard": 1,
        },
        {
            "type": "Link",
            "label": "Import sao kê ngân hàng",
            "link_type": "DocType",
            "link_to": "Bank Statement Import",
            "onboard": 1,
        },
        {
            "type": "Link",
            "label": "Giao dịch sao kê",
            "link_type": "DocType",
            "link_to": "Bank Statement Transaction",
        },
        {"type": "Card Break", "label": "Vận chuyển - đối soát"},
        {
            "type": "Link",
            "label": "Đối soát đơn vị vận chuyển",
            "link_type": "DocType",
            "link_to": "Carrier Settlement",
            "onboard": 1,
        },
        {
            "type": "Link",
            "label": "Cấu hình vận hành GUSA",
            "link_type": "DocType",
            "link_to": "GUSA Operations Settings",
        },
        {"type": "Card Break", "label": "Báo cáo nhanh"},
        {
            "type": "Link",
            "label": "Claim đã xác nhận chưa hạch toán",
            "link_type": "Report",
            "link_to": "Sales Payment Claims Confirmed Not Booked",
            "is_query_report": 1,
        },
        {
            "type": "Link",
            "label": "Tổng hợp claim thanh toán",
            "link_type": "Report",
            "link_to": "Sales Payment Claims Summary",
            "is_query_report": 1,
        },
        {
            "type": "Link",
            "label": "COD chưa đối soát",
            "link_type": "Report",
            "link_to": "COD Pending Cash",
            "is_query_report": 1,
        },
    ]

    doc = (
        frappe.get_doc("Workspace", "GUSA Operations")
        if frappe.db.exists("Workspace", "GUSA Operations")
        else frappe.new_doc("Workspace")
    )
    doc.update(
        {
            "name": "GUSA Operations",
            "title": "GUSA Operations",
            "label": "GUSA Operations",
            "module": "GUSA Custom",
            "public": 1,
            "icon": "organization",
            "sequence_id": 3,
            "content": "[]",
        }
    )
    doc.set("links", [])
    for idx, link in enumerate(links, start=1):
        link.setdefault("hidden", 0)
        link.setdefault("onboard", 0)
        link["idx"] = idx
        doc.append("links", link)

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

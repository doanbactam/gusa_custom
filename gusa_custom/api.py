import frappe


@frappe.whitelist()
def healthcheck():
    return {
        "app": "gusa_custom",
        "installed": True,
        "site": frappe.local.site,
    }

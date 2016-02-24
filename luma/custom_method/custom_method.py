
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
import frappe.utils
from frappe.utils import cstr, flt, getdate, comma_and, cint
from frappe import _
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.stock_balance import update_bin_qty, get_reserved_qty
from frappe.desk.notifications import clear_doctype_notifications
from erpnext.controllers.recurring_document import month_map, get_next_date

from erpnext.controllers.selling_controller import SellingController

@frappe.whitelist()
def make_delivery_note_cs(source_name=None, target_doc=None, item_code=None, test_list=None):
	# frappe.msgprint(test_list)
	test_list_json = json.loads(test_list)
	# frappe.msgprint(len(test_list_json))
	# frappe.msgprint(test_list_json[1])
	for source_name in test_list_json:
		def set_missing_values(source, target):
			if source.po_no:
				if target.po_no:
					target_po_no = target.po_no.split(", ")
					target_po_no.append(source.po_no)
					target.po_no = ", ".join(list(set(target_po_no))) if len(target_po_no) > 1 else target_po_no[0]
				else:
					target.po_no = source.po_no

			target.ignore_pricing_rule = 1
			target.run_method("set_missing_values")
			target.run_method("calculate_taxes_and_totals")

		def update_item(source, target, source_parent):
			target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
			target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
			target.qty = flt(source.qty) - flt(source.delivered_qty)

		target_doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1 and doc.item_code==item_code
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		},
	}, target_doc, set_missing_values)

	return target_doc

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, item_code=None, test_list=None):
	def set_missing_values(source, target):
		if source.po_no:
			if target.po_no:
				target_po_no = target.po_no.split(", ")
				target_po_no.append(source.po_no)
				target.po_no = ", ".join(list(set(target_po_no))) if len(target_po_no) > 1 else target_po_no[0]
			else:
				target.po_no = source.po_no

		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = flt(source.qty) - flt(source.delivered_qty)

	target_doc = get_mapped_doc("Sales Order", source_name, {
		"Sales Order": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Order Item": {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1 and doc.item_code==item_code
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		},
	}, target_doc, set_missing_values)

	frappe.msgprint(target_doc)
	return target_doc

@frappe.whitelist()
def get_so_details(item_code,customer):
	if not customer:
		frappe.throw("Please select Customer")
	# frappe.msgprint("in py")
	# frappe.msgprint(item_code)
	return {
	# "get_test_data": frappe.db.sql("""select name,customer from `tabSales Order` where customer='%s' and docstatus=1 order by name"""%(customer), as_list=1)
	"get_test_data": frappe.db.sql("""select so.name, si.qty, si.rate, so.delivery_date,si.item_code 
		from `tabSales Order` as so, `tabSales Order Item` si 
		where si.parent=so.name and so.docstatus=1 and so.customer='%s' and si.item_code='%s' order by so.delivery_date"""%(customer,item_code), as_list=1)
	}
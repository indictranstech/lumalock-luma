
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
from datetime import datetime, timedelta,date

@frappe.whitelist()
def make_delivery_note_cs(source_name=None, target_doc=None, item_code=None, test_list=None):
	test_list_json = json.loads(test_list)
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
def make_purchase_receipt(source_name=None, target_doc=None, item_code=None, po_list=None, po_row_list=None):
	po_list = json.loads(po_list)
	po_row_list = json.loads(po_row_list)
	for po_no in set(po_list):
		def set_missing_values(source, target):

			target.ignore_pricing_rule = 1
			target.run_method("set_missing_values")
			target.run_method("calculate_taxes_and_totals")

		def update_item(obj, target, source_parent):
			target.qty = flt(obj.qty) - flt(obj.received_qty)
			target.stock_qty = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.conversion_factor)
			target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)
			target.base_amount = (flt(obj.qty) - flt(obj.received_qty)) * \
				flt(obj.rate) * flt(source_parent.conversion_rate)
	
		target_doc = get_mapped_doc("Purchase Order", po_no,	{
			"Purchase Order": {
				"doctype": "Purchase Receipt",
				"validation": {
					"docstatus": ["=", 1],
				}
			},
			"Purchase Order Item": {
				"doctype": "Purchase Receipt Item",
				"field_map": {
					"name": "purchase_order_item",
					"parent": "purchase_order",
				},
				"postprocess": update_item,
				"condition": lambda doc: abs(doc.received_qty) < abs(doc.qty) \
							and doc.delivered_by_supplier!=1 \
							and doc.item_code==item_code \
							and doc.name in po_row_list
			},
			"Purchase Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
				"add_if_empty": True
			}
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

	return {
	"get_test_data": frappe.db.sql("""select so.name, si.qty, si.rate, si.delivered_qty, so.delivery_date, si.stock_uom, c.symbol, si.item_code 
		from `tabSales Order` as so, `tabSales Order Item` si, tabCurrency c 
		where si.parent=so.name and c.name=so.currency and so.docstatus=1
		and so.status != "Closed"
		and so.customer='%s' and si.item_code='%s' and si.delivered_qty<si.qty order by so.delivery_date"""%(customer,item_code), as_list=1)
	}

@frappe.whitelist()
def get_po_details(item_code, supplier):
	if not supplier:
		frappe.throw("Please select Supplier")
	return {
	"get_test_data": frappe.db.sql("""select po.name, pi.qty, pi.rate, ( pi.qty - pi.received_qty), po.transaction_date, pi.stock_uom, pi.item_code, pi.name as poi_row_name 
		from `tabPurchase Order` as po, `tabPurchase Order Item` pi, tabCurrency c 
		where pi.parent=po.name and c.name=po.currency and po.docstatus=1 
		and po.supplier='%s' and pi.item_code='%s' and pi.received_qty<pi.qty 
		and po.status != 'Closed' order by po.transaction_date"""%(supplier,item_code), as_list=1)
	}




@frappe.whitelist()	
def get_items_from_production_order(item_code):
	return frappe.db.sql("""select t1.item_code,t1.description,t2.name,date_format(t2.planned_start_date,'%d-%m-%Y') as date,
							(t2.qty - t2.produced_qty) as qty 
							from `tabItem`t1,`tabProduction Order`t2 
							where t1.item_code = '{0}' and t2.name in (select name from `tabProduction Order` where production_item = '{0}' 
							and docstatus = 1 and status != "Cancelled" and status != "Stopped") 
							order by date asc""".format(item_code),as_dict=1)

# def get_items_from_production_order(production_order):
# 	return frappe.db.sql("""select t1.item_code,t1.description,t2.name,date_format(t2.planned_start_date,'%d-%m-%Y') as date,
# 							(t2.qty - t2.custom_manufactured_qty - t2.produced_qty) as qty 
# 							from `tabItem`t1,`tabProduction Order`t2 
# 							where t1.item_code = t2.production_item 
# 							and t2.name ='{0}' order by date asc""".format(production_order),as_dict=1,debug=1)

@frappe.whitelist()	
def get_items_from_po(supplier,item_code):
	return frappe.db.sql("""select t1.item_code,t1.description,t2.name,(t1.qty - t1.received_qty) as qty,
							t1.price_list_rate,((t1.qty - t1.received_qty) * t1.price_list_rate) as amount,t2.transaction_date
							from `tabPurchase Order Item`t1 ,`tabPurchase Order`t2 
							where t1.parent = t2.name and t2.supplier = "{0}" 
							and t1.item_code = "{1}" and t2.docstatus = 1  order by t2.transaction_date asc """.format(supplier,item_code),as_dict=1)

# @frappe.whitelist()	
# def update_custom_received_qty(update_po):
# 	update_po = json.loads(update_po)
# 	for i in update_po:
# 		change_custom_received_qty(i['purchase_order'],i['item_code'],i['qty'])
		
# def change_custom_received_qty(purchase_order,item_code,qty):
# 	purchase_order = frappe.get_doc("Purchase Order",purchase_order)
# 	for row in purchase_order.items:
# 		if row.item_code == item_code:
# 			row.custom_received_qty = row.custom_received_qty + qty
# 			row.save(ignore_permissions = True)

# @frappe.whitelist()
# def update_custom_manufactured_qty(update_production_order):
# 	update_production_order = json.loads(update_production_order)
# 	for i in update_production_order:
# 		change_custom_manufactured_qty(i['production_order'],i['item_code'],i['qty'])
		
# def change_custom_manufactured_qty(production_order,item_code,qty):
# 	production_order = frappe.get_doc("Production Order",production_order)
# 	if item_code == production_order.production_item and (qty <= float(production_order.qty) - float(production_order.total_manufactured_qty)):
# 		print "in my cond"
# 		production_order.custom_manufactured_qty = production_order.custom_manufactured_qty + qty
# 		production_order.total_manufactured_qty = production_order.custom_manufactured_qty + production_order.produced_qty
# 		production_order.save(ignore_permissions = True)
# 	else:
# 		frappe.throw(_("Manufactured Qty > Production Order QTY"))

@frappe.whitelist()
def filter_items(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select item_code,item_name from `tabPurchase Order Item`t1,
							`tabPurchase Order`t2 where t1.parent = t2.name 
							and t2.supplier = '{0}' and t2.docstatus = 1
							and (item_name like '{txt}' or item_code like '{txt}' )limit 20""".format(filters['supplier'],txt= "%%%s%%" % txt),as_list=1)


def filter_production_items(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select distinct production_item from `tabProduction Order`
							where docstatus = 1 and status != "Cancelled" and status != "Stopped"
							and qty - produced_qty > 0
							and production_item like '{txt}' limit 20 """.format(txt= "%%%s%%" % txt),as_list=1)	

@frappe.whitelist()
def get_format_list(naming_series):
	if naming_series == "SINV-":	
		return 'Sales SINV'
	if naming_series == "SINV-RET-":	
		return 'Sales RET'


@frappe.whitelist()
def get_general_enquiry(item_code):
	sales_orders_query = """ select so.name, 
					   so.customer, 
					   soi.qty,
					   FORMAT(soi.rate, 2) as rate,
					   (soi.qty-soi.delivered_qty) as pending_qty,
					   so.delivery_date 
				from `tabSales Order` so, 
					 `tabSales Order Item` soi 
				where so.name=soi.parent 
					and soi.item_code='%s' and so.docstatus=1 and so.status != "Closed" """%(item_code)

	sales_orders = frappe.db.sql(sales_orders_query, as_dict=True)
	if len(sales_orders) > 0:

		sales_order = frappe.get_doc("Sales Order",sales_orders[0]['name'])
		currency = frappe.get_doc("Currency",sales_order.currency)
		
		for i in sales_orders:
			i["currency"] = currency.symbol


	purchase_orders_query = """ select po.name,
					   po.supplier,
					   poi.qty,
					   (poi.qty-poi.received_qty) as pending_qty,
					   FORMAT(poi.rate, 2) as rate,
					   FORMAT(((poi.qty-poi.received_qty)*poi.rate), 2) as amount,
					   po.transaction_date
				from `tabPurchase Order` po, 
					 `tabPurchase Order Item` poi 
				where po.name=poi.parent
					and poi.item_code='%s' and po.docstatus=1 and po.status != "Closed" """%(item_code)

	purchase_orders = frappe.db.sql(purchase_orders_query, as_dict=True)
	if len(purchase_orders) > 0:

		purchase_order = frappe.get_doc("Purchase Order",purchase_orders[0]['name'])
		currency = frappe.get_doc("Currency",purchase_order.currency)
		
		for i in purchase_orders:
			i["currency"] = currency.symbol	
		print purchase_orders,"purchase_orders updated"	




	production_orders_query = """ select pro.production_item,
								   pro.description,
								   pro.name,
								   (pro.qty - pro.produced_qty) as pending_qty,
								   pro.planned_start_date
								   
				from `tabProduction Order` as pro 
				where pro.production_item='%s' and pro.docstatus=1 
				and pro.status in ("Submitted","In Process") """%(item_code)

	production_orders = frappe.db.sql(production_orders_query, as_dict=True)

	frappe.errprint(production_orders)
	for i in production_orders:
		i["planned_start_date"] = i['planned_start_date'].date()

	return {
		"sales_orders": sales_orders,
		"purchase_orders": purchase_orders,
		"production_orders": production_orders
	}

@frappe.whitelist()
def make_new_po(source_name, target_doc=None):
	print source_name

	target_doc = get_mapped_doc("Purchase Order", source_name,
		{
			"Purchase Order": {
				"doctype": "Purchase Order",
			},
		}, target_doc)
	
	target_doc.parent_name = source_name
	return target_doc

@frappe.whitelist()
def update_parent_po(po):
	po = frappe.get_doc("Purchase Order",po)
	if not po.po_closed:
		po.update({
			"po_closed":"Yes"
			})
		po.save(ignore_permissions=True)
	return "parent po updated"



@frappe.whitelist()
def get_bom_children():
	if frappe.form_dict.parent:
		response = frappe.db.sql("""select item_code,
			bom_no as value, qty,
			if(ifnull(bom_no, "")!="", 1, 0) as expandable
			from `tabBOM Item`
			where parent=%s
			order by idx
			""", frappe.form_dict.parent, as_dict=True)

		for row in response:
			if not row.get("expandable", 0):
				row["stock"] = frappe.db.get_value("Bin", {"warehouse":"Luma Products - SWIE", \
					"item_code":row.get("item_code")}, "ifnull(round(actual_qty, 2), 0)") or 0.00
				row["remaining_qty"] = get_remaining_qty(row.get("item_code"))
		return response

def get_remaining_qty(item_code):
	count = frappe.db.sql(""" select 
						sum(`tabPurchase Order Item`.stock_qty - (ifnull(`tabPurchase Order Item`.received_qty, 0) * 
						ifnull(`tabPurchase Order Item`.conversion_factor, 0)) ) as qty_to_receive
					from
						`tabPurchase Order`, `tabPurchase Order Item`
					where
						`tabPurchase Order Item`.`parent` = `tabPurchase Order`.`name`
						and `tabPurchase Order`.docstatus = 1
						and `tabPurchase Order`.status not in ("Stopped", "Closed")
						and `tabPurchase Order Item`.item_code = '{0}' """
						.format(frappe.db.escape(item_code)), as_dict=1)
	return count and count[0].get("qty_to_receive", 0) or 0

@frappe.whitelist()
def get_outerbox_item(item_code):
	item_data = {}
	item_doc = frappe.get_doc("Item",item_code)
	if item_doc.outer_box_code:
		outerbox_doc = frappe.get_doc("Item",item_doc.outer_box_code)
		item_data['outbox_wt'] = outerbox_doc.net_weight
		item_data['outbox_length'] = outerbox_doc.length
		item_data['outbox_height'] = outerbox_doc.height
		item_data['outbox_width'] = outerbox_doc.width
		item_data['description'] = outerbox_doc.description
	if item_doc.inner_box_code:
		innerbox_doc = frappe.get_doc("Item",item_doc.inner_box_code)
		item_data['inbox_wt'] = innerbox_doc.net_weight
	if item_doc.outer_box_code:
		item_data['outer_box_code'] = item_doc.outer_box_code
	item_data['nt_wt'] = item_doc.net_weight
	return item_data


@frappe.whitelist()
def set_item_values(doc, method):
	print "into the hooks file_____________________________",doc.doctype,method
	material_request = ""
	for row in doc.items:
		if row.item_code:
			row.outer_box_qty = round(flt(row.qty / flt(row.outer_box_pcs) ),2) if row.outer_box_pcs else 0
			row.inner_box_qty = round(flt(row.qty/ flt(row.inner_box_pcs) ), 2) if row.inner_box_pcs else 0
			row.total_volume = round(flt(row.length_new * row.width * row.height * row.outer_box_qty)/1000000000, 3)
			row.total_net_weight = round(flt(row.item_net_weight1 * row.qty),2)
			row.total_gross_weight1 = round(flt(row.qty*row.item_net_weight1 + (row.outer_box_qty*row.outer_box_weight)+(row.inner_box_qty*row.inner_box_weight)),2)
			if doc.doctype == 'Delivery Note':
				print "for ___________ADRchecjk###############"
				row.total_adr_weight = round(flt(row.qty*row.adr_weight),2)
				print "___________________",row.total_adr_weight
		material_request = row.material_request  or "" 
	
	#below code only for AWS server
	if row.material_request:
		data = get_customer_detail(material_request)
		doc.sales_order_no = data.name or ""
		doc.customer_name_so = data.customer or ""
		doc.customer_address = data.shipping_address or ""
		doc.customers_purchase_order = data.po_no or ""
		doc.proforma_invoice_no = frappe.db.get_value("Sales Order Item",{'parent':data.name},'prevdoc_docname') or ""

def get_customer_detail(material_request):
	so_no = frappe.db.get_value("Material Request Item",{'parent':material_request},['sales_order'])
	so_doc = frappe.get_doc("Sales Order",so_no)
	return so_doc
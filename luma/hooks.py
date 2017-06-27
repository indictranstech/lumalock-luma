# -*- coding: utf-8 -*-
from __future__ import unicode_literals

app_name = "luma"
app_title = "luma"
app_publisher = "New Indictrans Technologies Pvt Ltd"
app_description = "app"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "sambhaji.k@indictranstech.com"
app_version = "0.0.1"
app_license = "MIT"
fixtures = ["Custom Script"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "assets/css/luma.min.css"
app_include_js = "/assets/js/luma.min.js"

# include js, css files in header of web template
# web_include_css = "/assets/luma/css/luma.css"
# web_include_js = "/assets/luma/js/luma.js"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "luma.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "luma.install.before_install"
# after_install = "luma.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "luma.notifications.get_notification_config"

# Add Fixtures
fixtures =['Custom Field', "Property Setter","Custom Script","Print Format", "Role"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Delivery Note": {
		"validate":"luma.custom_method.item.item_logistic"
	},
	"Packing Slip": {
		"validate":"luma.custom_method.item.packing_weight"
	},
	"Purchase Order": {
		"before_save":"luma.custom_method.custom_method.set_item_values"
	},
	"Delivery Note": {
		"before_save":"luma.custom_method.custom_method.set_item_values"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"luma.tasks.all"
# 	],
# 	"daily": [
# 		"luma.tasks.daily"
# 	],
# 	"hourly": [
# 		"luma.tasks.hourly"
# 	],
# 	"weekly": [
# 		"luma.tasks.weekly"
# 	]
# 	"monthly": [
# 		"luma.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "luma.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "luma.event.get_events"
# }


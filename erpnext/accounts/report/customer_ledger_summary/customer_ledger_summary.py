# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, qb, scrub
<<<<<<< HEAD
=======
from frappe.query_builder import Criterion, Tuple
from frappe.query_builder.functions import IfNull
>>>>>>> e84e49345a (perf: refactored customer ledger summary for performance)
from frappe.utils import getdate, nowdate
from frappe.utils.nestedset import get_descendants_of

<<<<<<< HEAD
=======
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)

TREE_DOCTYPES = frozenset(
	["Customer Group", "Terrirtory", "Supplier Group", "Sales Partner", "Sales Person", "Cost Center"]
)

>>>>>>> fca46e0b2d (fix: child values for tree doctypes and query refactor)

class PartyLedgerSummaryReport:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

	def run(self, args):
		self.filters.party_type = args.get("party_type")
<<<<<<< HEAD
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
=======
>>>>>>> fca46e0b2d (fix: child values for tree doctypes and query refactor)

		self.validate_filters()
		self.get_paty_details()

		if not self.parties:
			return [], []

		self.get_gl_entries()
		self.get_return_invoices()
		self.get_party_adjustment_amounts()

		self.party_naming_by = frappe.db.get_single_value(args.get("naming_by")[0], args.get("naming_by")[1])
		columns = self.get_columns()
		data = self.get_data()

		return columns, data

	def validate_filters(self):
		if not self.filters.get("company"):
			frappe.throw(_("{0} is mandatory").format(_("Company")))

		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		self.update_hierarchical_filters()

	def update_hierarchical_filters(self):
		for doctype in TREE_DOCTYPES:
			key = scrub(doctype)
			if self.filters.get(key):
				self.filters[key] = get_children(doctype, self.filters[key])

	def get_paty_details(self):
		"""
		Additional Columns for 'User Permission' based access control
		"""
		self.parties = []
		self.party_details = frappe._dict()
		party_type = self.filters.party_type

		doctype = qb.DocType(party_type)
		conditions = self.get_party_conditions(doctype)
		query = (
			qb.from_(doctype)
			.select(doctype.name.as_("party"), f"{scrub(party_type)}_name")
			.where(Criterion.all(conditions))
		)

		from frappe.desk.reportview import build_match_conditions

		query, params = query.walk()
		match_conditions = build_match_conditions(party_type)

		if match_conditions:
			query += "and" + match_conditions

		party_details = frappe.db.sql(query, params, as_dict=True)

		for row in party_details:
			self.parties.append(row.party)
			self.party_details[row.party] = row

	def get_party_conditions(self, doctype):
		conditions = []
		group_field = "customer_group" if self.filters.party_type == "Customer" else "supplier_group"

		if self.filters.party:
			conditions.append(doctype.name == self.filters.party)

		if self.filters.territory:
			conditions.append(doctype.territory.isin(self.filters.territory))

		if self.filters.get(group_field):
			conditions.append(doctype.get(group_field).isin(self.filters.get(group_field)))

		if self.filters.payment_terms_template:
			conditions.append(doctype.payment_terms == self.filters.payment_terms_template)

		if self.filters.sales_partner:
			conditions.append(doctype.default_sales_partner.isin(self.filters.sales_partner))

		if self.filters.sales_person:
			sales_team = qb.DocType("Sales Team")
			sales_invoice = qb.DocType("Sales Invoice")

			customers = (
				qb.from_(sales_team)
				.select(sales_team.parent)
				.where(sales_team.sales_person.isin(self.filters.sales_person))
				.where(sales_team.parenttype == "Customer")
			) + (
				qb.from_(sales_team)
				.join(sales_invoice)
				.on(sales_team.parent == sales_invoice.name)
				.select(sales_invoice.customer)
				.where(sales_team.sales_person.isin(self.filters.sales_person))
				.where(sales_team.parenttype == "Sales Invoice")
			)

			conditions.append(doctype.name.isin(customers))

		return conditions

	def get_columns(self):
		columns = [
			{
				"label": _(self.filters.party_type),
				"fieldtype": "Link",
				"fieldname": "party",
				"options": self.filters.party_type,
				"width": 200,
			}
		]

		if self.party_naming_by == "Naming Series":
			columns.append(
				{
					"label": _(self.filters.party_type + "Name"),
					"fieldtype": "Data",
					"fieldname": "party_name",
					"width": 110,
				}
			)

		credit_or_debit_note = "Credit Note" if self.filters.party_type == "Customer" else "Debit Note"

		columns += [
			{
				"label": _("Opening Balance"),
				"fieldname": "opening_balance",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Invoiced Amount"),
				"fieldname": "invoiced_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Paid Amount"),
				"fieldname": "paid_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _(credit_or_debit_note),
				"fieldname": "return_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
		]

		for account in self.party_adjustment_accounts:
			columns.append(
				{
					"label": account,
					"fieldname": "adj_" + scrub(account),
					"fieldtype": "Currency",
					"options": "currency",
					"width": 120,
					"is_adjustment": 1,
				}
			)

		columns += [
			{
				"label": _("Closing Balance"),
				"fieldname": "closing_balance",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"label": _("Currency"),
				"fieldname": "currency",
				"fieldtype": "Link",
				"options": "Currency",
				"width": 50,
			},
		]

		# Hidden columns for handling 'User Permissions'
		if self.filters.party_type == "Customer":
			columns += [
				{
					"label": _("Territory"),
					"fieldname": "territory",
					"fieldtype": "Link",
					"options": "Territory",
					"hidden": 1,
				},
				{
					"label": _("Customer Group"),
					"fieldname": "customer_group",
					"fieldtype": "Link",
					"options": "Customer Group",
					"hidden": 1,
				},
			]
		else:
			columns += [
				{
					"label": _("Supplier Group"),
					"fieldname": "supplier_group",
					"fieldtype": "Link",
					"options": "Supplier Group",
					"hidden": 1,
				}
			]

		return columns

	def get_data(self):
		company_currency = frappe.get_cached_value("Company", self.filters.get("company"), "default_currency")
		invoice_dr_or_cr = "debit" if self.filters.party_type == "Customer" else "credit"
		reverse_dr_or_cr = "credit" if self.filters.party_type == "Customer" else "debit"

		self.party_data = frappe._dict({})
		for gle in self.gl_entries:
			party_details = self.party_details.get(gle.party)
			self.party_data.setdefault(
				gle.party,
				frappe._dict(
					{
						**party_details,
						"party_name": gle.party,
						"opening_balance": 0,
						"invoiced_amount": 0,
						"paid_amount": 0,
						"return_amount": 0,
						"closing_balance": 0,
						"currency": company_currency,
					}
				),
			)

			amount = gle.get(invoice_dr_or_cr) - gle.get(reverse_dr_or_cr)
			self.party_data[gle.party].closing_balance += amount

			if gle.posting_date < self.filters.from_date or gle.is_opening == "Yes":
				self.party_data[gle.party].opening_balance += amount
			else:
				if amount > 0:
					self.party_data[gle.party].invoiced_amount += amount
				elif gle.voucher_no in self.return_invoices:
					self.party_data[gle.party].return_amount -= amount
				else:
					self.party_data[gle.party].paid_amount -= amount

		out = []
		for party, row in self.party_data.items():
			if (
				row.opening_balance
				or row.invoiced_amount
				or row.paid_amount
				or row.return_amount
				or row.closing_amount
			):
				total_party_adjustment = sum(
					amount for amount in self.party_adjustment_details.get(party, {}).values()
				)
				row.paid_amount -= total_party_adjustment

				adjustments = self.party_adjustment_details.get(party, {})
				for account in self.party_adjustment_accounts:
					row["adj_" + scrub(account)] = adjustments.get(account, 0)

				out.append(row)

		return out

	def get_gl_entries(self):
<<<<<<< HEAD
		conditions = self.prepare_conditions()
		join = join_field = ""
		if self.filters.party_type == "Customer":
			join_field = ", p.customer_name as party_name"
			join = "left join `tabCustomer` p on gle.party = p.name"
		elif self.filters.party_type == "Supplier":
			join_field = ", p.supplier_name as party_name"
			join = "left join `tabSupplier` p on gle.party = p.name"

		self.gl_entries = frappe.db.sql(
			f"""
			select
				gle.posting_date, gle.party, gle.voucher_type, gle.voucher_no, gle.against_voucher_type,
				gle.against_voucher, gle.debit, gle.credit, gle.is_opening {join_field}
			from `tabGL Entry` gle
			{join}
			where
				gle.docstatus < 2 and gle.is_cancelled = 0 and gle.party_type=%(party_type)s and ifnull(gle.party, '') != ''
				and gle.posting_date <= %(to_date)s {conditions}
			order by gle.posting_date
		""",
			self.filters,
			as_dict=True,
		)

	def prepare_conditions(self):
		conditions = [""]

=======
		gle = qb.DocType("GL Entry")
		query = (
			qb.from_(gle)
			.select(
				gle.posting_date,
				gle.party,
				gle.voucher_type,
				gle.voucher_no,
				gle.debit,
				gle.credit,
				gle.is_opening,
			)
			.where(
				(gle.docstatus < 2)
				& (gle.is_cancelled == 0)
				& (gle.party_type == self.filters.party_type)
				& (IfNull(gle.party, "") != "")
				& (gle.posting_date <= self.filters.to_date)
				& (gle.party.isin(self.parties))
			)
		)

		query = self.prepare_conditions(query)

		self.gl_entries = query.run(as_dict=True)

	def prepare_conditions(self, query):
		gle = qb.DocType("GL Entry")
>>>>>>> e84e49345a (perf: refactored customer ledger summary for performance)
		if self.filters.company:
			conditions.append("gle.company=%(company)s")

		if self.filters.finance_book:
			conditions.append("ifnull(finance_book,'') in (%(finance_book)s, '')")

<<<<<<< HEAD
		if self.filters.get("party"):
			conditions.append("party=%(party)s")

		if self.filters.party_type == "Customer":
			if self.filters.get("customer_group"):
				lft, rgt = frappe.get_cached_value(
					"Customer Group", self.filters["customer_group"], ["lft", "rgt"]
				)

				conditions.append(
					f"""party in (select name from tabCustomer
					where exists(select name from `tabCustomer Group` where lft >= {lft} and rgt <= {rgt}
						and name=tabCustomer.customer_group))"""
				)

			if self.filters.get("territory"):
				lft, rgt = frappe.db.get_value("Territory", self.filters.get("territory"), ["lft", "rgt"])

				conditions.append(
					f"""party in (select name from tabCustomer
					where exists(select name from `tabTerritory` where lft >= {lft} and rgt <= {rgt}
						and name=tabCustomer.territory))"""
				)

			if self.filters.get("payment_terms_template"):
				conditions.append(
					"party in (select name from tabCustomer where payment_terms=%(payment_terms_template)s)"
				)

			if self.filters.get("sales_partner"):
				conditions.append(
					"party in (select name from tabCustomer where default_sales_partner=%(sales_partner)s)"
				)

			if self.filters.get("sales_person"):
				lft, rgt = frappe.db.get_value(
					"Sales Person", self.filters.get("sales_person"), ["lft", "rgt"]
				)

				conditions.append(
					"""exists(select name from `tabSales Team` steam where
					steam.sales_person in (select name from `tabSales Person` where lft >= {} and rgt <= {})
					and ((steam.parent = voucher_no and steam.parenttype = voucher_type)
						or (steam.parent = against_voucher and steam.parenttype = against_voucher_type)
						or (steam.parent = party and steam.parenttype = 'Customer')))""".format(lft, rgt)
				)

		if self.filters.party_type == "Supplier":
			if self.filters.get("supplier_group"):
				conditions.append(
					"""party in (select name from tabSupplier
					where supplier_group=%(supplier_group)s)"""
				)

		return " and ".join(conditions)
=======
		if self.filters.cost_center:
			query = query.where((gle.cost_center).isin(self.filters.cost_center))

		if self.filters.project:
			query = query.where((gle.project).isin(self.filters.project))

		accounting_dimensions = get_accounting_dimensions(as_list=False)

		if accounting_dimensions:
			for dimension in accounting_dimensions:
				if self.filters.get(dimension.fieldname):
					if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
						self.filters[dimension.fieldname] = get_dimension_with_children(
							dimension.document_type, self.filters.get(dimension.fieldname)
						)
						query = query.where(
							(gle[dimension.fieldname]).isin(self.filters.get(dimension.fieldname))
						)
					else:
						query = query.where(
							(gle[dimension.fieldname]).isin(self.filters.get(dimension.fieldname))
						)

		return query
>>>>>>> e84e49345a (perf: refactored customer ledger summary for performance)

	def get_return_invoices(self):
		doctype = "Sales Invoice" if self.filters.party_type == "Customer" else "Purchase Invoice"
		filters = (
			{
				"is_return": 1,
				"docstatus": 1,
				"posting_date": ["between", [self.filters.from_date, self.filters.to_date]],
				f"{scrub(self.filters.party_type)}": ["in", self.parties],
			},
		)

		self.return_invoices = frappe.get_all(doctype, filters=filters, pluck="name")

	def get_party_adjustment_amounts(self):
		conditions = self.prepare_conditions()
		account_type = "Expense Account" if self.filters.party_type == "Customer" else "Income Account"
<<<<<<< HEAD
		income_or_expense_accounts = frappe.db.get_all(
			"Account", filters={"account_type": account_type, "company": self.filters.company}, pluck="name"
		)
=======

>>>>>>> e84e49345a (perf: refactored customer ledger summary for performance)
		invoice_dr_or_cr = "debit" if self.filters.party_type == "Customer" else "credit"
		reverse_dr_or_cr = "credit" if self.filters.party_type == "Customer" else "debit"
		round_off_account = frappe.get_cached_value("Company", self.filters.company, "round_off_account")

<<<<<<< HEAD
		gl = qb.DocType("GL Entry")
		if not income_or_expense_accounts:
			# prevent empty 'in' condition
			income_or_expense_accounts.append("")
		else:
			# escape '%' in account name
			# ignoring frappe.db.escape as it replaces single quotes with double quotes
			income_or_expense_accounts = [x.replace("%", "%%") for x in income_or_expense_accounts]

		accounts_query = (
=======
		current_period_vouchers = set()
		adjustment_voucher_entries = {}

		self.party_adjustment_details = {}
		self.party_adjustment_accounts = set()

		for gle in self.gl_entries:
			if (
				gle.is_opening != "Yes"
				and gle.posting_date >= self.filters.from_date
				and gle.posting_date <= self.filters.to_date
			):
				current_period_vouchers.add((gle.voucher_type, gle.voucher_no))
				adjustment_voucher_entries.setdefault((gle.voucher_type, gle.voucher_no), []).append(gle)

		if not current_period_vouchers:
			return

		gl = qb.DocType("GL Entry")
		query = (
>>>>>>> e84e49345a (perf: refactored customer ledger summary for performance)
			qb.from_(gl)
			.select(gl.voucher_type, gl.voucher_no)
			.where(
<<<<<<< HEAD
				(gl.account.isin(income_or_expense_accounts))
				& (gl.posting_date.gte(self.filters.from_date))
				& (gl.posting_date.lte(self.filters.to_date))
			)
		)

		gl_entries = frappe.db.sql(
			f"""
			select
				posting_date, account, party, voucher_type, voucher_no, debit, credit
			from
				`tabGL Entry`
			where
				docstatus < 2 and is_cancelled = 0
				and (voucher_type, voucher_no) in (
				{accounts_query}
				) and (voucher_type, voucher_no) in (
					select voucher_type, voucher_no from `tabGL Entry` gle
					where gle.party_type=%(party_type)s and ifnull(party, '') != ''
					and gle.posting_date between %(from_date)s and %(to_date)s and gle.docstatus < 2 {conditions}
				)
			""",
			self.filters,
			as_dict=True,
		)
=======
				(gl.docstatus < 2)
				& (gl.is_cancelled == 0)
				& (gl.posting_date.gte(self.filters.from_date))
				& (gl.posting_date.lte(self.filters.to_date))
				& (Tuple((gl.voucher_type, gl.voucher_no)).isin(current_period_vouchers))
				& (IfNull(gl.party, "") == "")
			)
		)
		query = self.prepare_conditions(query)
		gl_entries = query.run(as_dict=True)
>>>>>>> e84e49345a (perf: refactored customer ledger summary for performance)

		for gle in gl_entries:
			adjustment_voucher_entries[(gle.voucher_type, gle.voucher_no)].append(gle)

		for voucher_gl_entries in adjustment_voucher_entries.values():
			parties = {}
			accounts = {}
			has_irrelevant_entry = False

			for gle in voucher_gl_entries:
				if gle.account == round_off_account:
					continue
				elif gle.party:
					parties.setdefault(gle.party, 0)
					parties[gle.party] += gle.get(reverse_dr_or_cr) - gle.get(invoice_dr_or_cr)
				elif frappe.get_cached_value("Account", gle.account, "account_type") == account_type:
					accounts.setdefault(gle.account, 0)
					accounts[gle.account] += gle.get(invoice_dr_or_cr) - gle.get(reverse_dr_or_cr)
				else:
					has_irrelevant_entry = True

			if parties and accounts:
				if len(parties) == 1:
					party = next(iter(parties.keys()))
					for account, amount in accounts.items():
						self.party_adjustment_accounts.add(account)
						self.party_adjustment_details.setdefault(party, {})
						self.party_adjustment_details[party].setdefault(account, 0)
						self.party_adjustment_details[party][account] += amount
				elif len(accounts) == 1 and not has_irrelevant_entry:
					account = next(iter(accounts.keys()))
					self.party_adjustment_accounts.add(account)
					for party, amount in parties.items():
						self.party_adjustment_details.setdefault(party, {})
						self.party_adjustment_details[party].setdefault(account, 0)
						self.party_adjustment_details[party][account] += amount


def get_children(doctype, value):
	children = get_descendants_of(doctype, value)

	return [value, *children]


def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return PartyLedgerSummaryReport(filters).run(args)

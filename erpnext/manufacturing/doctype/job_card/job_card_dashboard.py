from frappe import _


def get_data():
	return {
		"fieldname": "job_card",
		"non_standard_fieldnames": {"Quality Inspection": "reference_name"},
		"transactions": [
			{"label": _("Transactions"), "items": ["Material Request", "Stock Entry"]},
<<<<<<< HEAD
=======
			{"label": _("Subcontracting"), "items": ["Purchase Order", "Subcontracting Order"]},
>>>>>>> 94d7e5964b (fix: add doc.status to translation from POS)
			{"label": _("Reference"), "items": ["Quality Inspection"]},
		],
	}

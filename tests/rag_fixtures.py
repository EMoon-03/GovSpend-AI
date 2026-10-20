"""Small offline fixtures shaped like the real sources."""

FAR_PART_6_HTML = """
<html><body>
<h1>Part 6 - Competition Requirements</h1>
<h4>6.000 Scope of part.</h4>
<p>This part prescribes policies and procedures to promote full and open competition
in the acquisition process.</p>
<h3>Subpart 6.3 - Other Than Full and Open Competition</h3>
<h4 id="FAR_6_302_1">6.302-1 Only one responsible source and no other supplies or services
will satisfy agency requirements.</h4>
<p>(a) <em>Authority.</em> When the supplies or services required are available from only one
responsible source, full and open competition need not be provided, as described in
<a href="/far/6.303">6.303</a>.</p>
<p>(b) <em>Application.</em> This authority applies when a follow-on contract would result
in substantial duplication of cost.</p>
<h4>6.303-2 Content.</h4>
<p>""" + ("Each justification shall contain sufficient facts and rationale to justify the use "
          "of the specific authority cited. ") * 30 + """</p>
<h4>16.505 Ordering.</h4>
<p>A cross-referenced heading from another part that must be ignored.</p>
<script>var x = "6.999 not a section";</script>
</body></html>
"""

DATA_DICTIONARY_PAYLOAD = {
    "document": {
        "metadata": {"total_rows": 3},
        "sections": [],
        "headers": [
            {"raw": "element", "display": "Element"},
            {"raw": "definition", "display": "Definition"},
            {"raw": "fpds_data_dictionary_element", "display": "FPDS Element"},
            {"raw": "grouping", "display": "Grouping"},
            {"raw": "domain_values", "display": "Domain Values"},
        ],
        "rows": [
            ["Total Obligated Amount", "The sum of all obligations on the award.", "obligatedAmount",
             "Award Amounts", None],
            ["Type of Contract Pricing", "The pricing arrangement of the contract.", "typeOfContractPricing",
             "Contract Details", "J: Firm Fixed Price; U: Cost Plus Fixed Fee"],
            ["Empty Definition", None, None, None, None],
        ],
    }
}


def make_awards(n_same=24):
    """n_same awards sharing NAICS 541512 at DoD, plus a few others."""
    rows = []
    for i in range(n_same):
        rows.append({
            "generated_internal_id": f"CONT_AWD_DOD_{i}", "award_id": f"W91{i:03d}",
            "recipient_name": f"Vendor {i % 5}", "award_amount": 100_000.0 * (i + 1),
            "awarding_agency": "Department of Defense", "awarding_sub_agency": "Department of the Army",
            "contract_award_type": "DELIVERY ORDER", "start_date": "2025-01-15",
            "naics_code": "541512", "naics_description": "COMPUTER SYSTEMS DESIGN SERVICES",
            "psc_code": "DA01", "psc_description": "IT AND TELECOM - BUSINESS APPLICATION",
            "description": ("CLOUD HOSTING AND MIGRATION SUPPORT" if i % 2 else
                            "HELP DESK AND END USER SUPPORT SERVICES"),
        })
    rows.append({
        "generated_internal_id": "CONT_AWD_BIG", "award_id": "W91BIG", "recipient_name": "Vendor X",
        "award_amount": 95_000_000.0, "awarding_agency": "Department of Defense",
        "awarding_sub_agency": "Department of the Army", "contract_award_type": "DEFINITIVE CONTRACT",
        "start_date": "2025-03-01", "naics_code": "541512",
        "naics_description": "COMPUTER SYSTEMS DESIGN SERVICES", "psc_code": "DA01",
        "psc_description": "IT AND TELECOM - BUSINESS APPLICATION",
        "description": "ENTERPRISE CLOUD HOSTING AND MIGRATION SUPPORT, MULTI-YEAR",
    })
    rows.append({
        "generated_internal_id": "CONT_AWD_HHS_1", "award_id": "HHS001", "recipient_name": "Vendor Y",
        "award_amount": 250_000.0, "awarding_agency": "Department of Health and Human Services",
        "awarding_sub_agency": None, "contract_award_type": "PURCHASE ORDER", "start_date": None,
        "naics_code": "541511", "naics_description": "CUSTOM COMPUTER PROGRAMMING SERVICES",
        "psc_code": None, "psc_description": None, "description": None,
    })
    return rows

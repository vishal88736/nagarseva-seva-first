"""Conservative PMAY-U 2.0 pathway screening with source and review date."""

SOURCE = "https://pmaymis.gov.in/pmaymis2_2024/PmayFAQ.aspx"
REVIEWED = "2026-10-11"


def screen(inputs: dict) -> dict:
    annual = inputs["monthly_income_inr"] * 12
    band = "EWS" if annual <= 300_000 else "LIG" if annual <= 600_000 else "MIG" if annual <= 900_000 else "above national screening band"
    reasons, pathways = [], []
    base_fields = ["urban_resident", "owns_pucca_house", "received_housing_benefit_last_20_years"]
    unanswered = [key for key in base_fields if inputs.get(key) is None]
    blocked = inputs.get("urban_resident") is False or inputs.get("owns_pucca_house") is True or inputs.get("received_housing_benefit_last_20_years") is True
    if blocked:
        reasons.append("One or more answers fall outside the national PMAY-U 2.0 screening conditions. Ask the ULB to verify your circumstances and other available programmes.")
    elif annual > 900_000:
        reasons.append("The declared annual household income exceeds the national EWS/LIG/MIG screening bands. State-specific provisions require authority verification.")
    else:
        if unanswered:
            reasons.append("Confirm urban residence, family ownership of a pucca house, and housing benefits received in the last 20 years before screening can be completed.")
        else:
            reasons.append("The declared urban residence, house ownership and prior-benefit answers meet the basic screening conditions; documentary verification is still required.")
        if annual <= 300_000:
            pathways.append("PMAY-U 2.0 — AHP")
            if inputs.get("owns_buildable_land") is True:
                pathways.append("PMAY-U 2.0 — BLC")
            elif inputs.get("owns_buildable_land") is None:
                reasons.append("BLC also needs ownership/approved rights to suitable vacant land; this has not been confirmed.")
        if annual <= 600_000 and inputs.get("wants_rental"):
            pathways.append("PMAY-U 2.0 — ARH")
        loan_limits = [("loan_amount_inr", 2_500_000), ("property_value_inr", 3_500_000), ("carpet_area_sqm", 120)]
        if not inputs.get("wants_rental") and all(inputs.get(key) is None or inputs[key] <= limit for key, limit in loan_limits):
            pathways.append("PMAY-U 2.0 — ISS")
            reasons.append("ISS additionally requires loan ≤ ₹25 lakh, house value ≤ ₹35 lakh, carpet area ≤ 120 sqm, and a qualifying loan sanctioned and disbursed on/after 1 September 2024; the lender must verify these checks.")
    return {"eligible_schemes": pathways, "pathways_to_verify": pathways, "annual_income_inr": annual, "income_band": band,
            "screening_status": "needs_information" if unanswered and not blocked else "authority_verification_required",
            "reasons": reasons, "documents_required": ["Identity proof", "Household income proof", "Address/residence proof", "Bank account details", "Land ownership/right documents for BLC", "House ownership and prior housing-benefit declarations"],
            "next_steps": ["Choose one suitable pathway with the ULB/approved lender", "Verify current state rules and the complete scheme conditions", "For SRA, request a statutory household/tenure review; settlement duration alone does not establish eligibility"],
            "source_url": SOURCE, "policy_version": "PMAY-U 2.0", "reviewed_on": REVIEWED,
            "disclaimer": "Indicative pathway screening using declared answers. Eligibility, benefits and approvals are determined by the relevant authority; no subsidy is guaranteed."}

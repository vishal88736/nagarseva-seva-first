"""Rules-based, auditable cross-subsidy feasibility simulator."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class FeasibilityInput:
    land_area_sqm: float
    fsi: float
    eligible_households: int
    rehab_area_sqft: float = 300
    construction_cost_per_sqft: float = 3200
    market_sale_rate_per_sqft: float = 14500
    tdr_value_per_sqft: float = 900
    premiums_and_fees_pct: float = 0.12
    sales_share_pct: float = 0.65
    cost_inflation_pct: float = 0


def simulate(params: FeasibilityInput | dict) -> dict:
    p = params if isinstance(params, FeasibilityInput) else FeasibilityInput(**params)
    if p.land_area_sqm <= 0 or p.fsi <= 0 or p.eligible_households < 0:
        raise ValueError("land_area_sqm, fsi and eligible_households must be positive")
    gross_area_sqft = p.land_area_sqm * 10.7639 * p.fsi
    free_rehab_area = p.eligible_households * p.rehab_area_sqft
    area_shortfall = max(free_rehab_area - gross_area_sqft, 0)
    physically_feasible = area_shortfall == 0
    saleable_area = max(gross_area_sqft - free_rehab_area, 0)
    effective_cost = p.construction_cost_per_sqft * (1 + p.cost_inflation_pct / 100)
    construction = gross_area_sqft * effective_cost
    fees = construction * p.premiums_and_fees_pct
    tdr_support = gross_area_sqft * p.tdr_value_per_sqft
    gross_sales = saleable_area * p.market_sale_rate_per_sqft * p.sales_share_pct
    total_support = gross_sales + tdr_support
    profit = total_support - construction - fees
    margin = profit / max(total_support, 1)
    sales_area = saleable_area * p.sales_share_pct
    break_even_rate = max(construction + fees - tdr_support, 0) / sales_area if sales_area > 0 and physically_feasible else None
    # An indicative project IRR, explicitly a screening proxy rather than a valuation.
    months = 36
    irr = (max(total_support, 1) / max(construction + fees, 1)) ** (12 / months) - 1
    verdict = "Viable" if profit >= 0 and irr >= .08 else "Borderline" if profit >= -construction * .1 else "Not viable"
    if not physically_feasible:
        verdict = "Not viable"
    return {"inputs": asdict(p), "physically_feasible": physically_feasible, "rehab_area_shortfall_sqft": round(area_shortfall), "gross_built_up_area_sqft": round(gross_area_sqft), "free_rehab_area_sqft": round(free_rehab_area), "saleable_area_sqft": round(saleable_area), "construction_cost_inr": round(construction), "fees_inr": round(fees), "tdr_support_inr": round(tdr_support), "gross_sales_support_inr": round(gross_sales), "developer_profit_inr": round(profit), "developer_margin_pct": round(margin * 100, 1), "indicative_irr_pct": round(irr * 100, 1), "break_even_market_rate_per_sqft": round(break_even_rate) if break_even_rate is not None else None, "verdict": verdict}


def sensitivity(params: FeasibilityInput | dict) -> list[dict]:
    base = params if isinstance(params, FeasibilityInput) else FeasibilityInput(**params)
    scenarios = [("Market rate", "market_sale_rate_per_sqft", -.2), ("Market rate", "market_sale_rate_per_sqft", .2), ("Construction inflation", "cost_inflation_pct", 10), ("FSI", "fsi", -.3), ("FSI", "fsi", .3)]
    result = []
    for label, attr, delta in scenarios:
        values = asdict(base)
        if attr == "cost_inflation_pct": values[attr] += delta
        else: values[attr] *= 1 + delta
        outcome = simulate(values)
        result.append({"factor": f"{label} {delta:+.0%}" if attr != "cost_inflation_pct" else f"{label} +{delta:.0f}%", "profit_inr": outcome["developer_profit_inr"], "margin_pct": outcome["developer_margin_pct"], "verdict": outcome["verdict"]})
    return sorted(result, key=lambda x: x["profit_inr"])

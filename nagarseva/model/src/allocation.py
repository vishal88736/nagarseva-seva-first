"""Budgeted pocket allocation with checked ward coverage and an actual equal-ward baseline."""

from __future__ import annotations

import math
from typing import Any
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix, vstack


def _options(pockets: pd.DataFrame) -> pd.DataFrame:
    frame = pockets.copy().reset_index(drop=True)
    if frame.empty:
        return frame
    frame["cost_inr"] = frame.population.fillna(0) * (9500 + frame.structural_risk_score.fillna(50) * 80)
    frame["impact"] = frame.population.fillna(0) * frame.priority_score.fillna(0) / 100
    # This is an explicit planning proxy, not a protected-group eligibility determination.
    frame["vulnerable"] = frame.priority_score.fillna(0) >= 65
    frame["ward_key"] = frame.city.astype(str) + " / " + frame.ward.astype(str)
    return frame.loc[frame.priority_score.notna() & (frame.cost_inr > 0) & np.isfinite(frame.cost_inr) & np.isfinite(frame.impact)].reset_index(drop=True)


def _solve(frame: pd.DataFrame, budget: float, share: float, wards_required: int, equal_ward: bool = False, seconds: float = 2) -> dict:
    empty = {"selected": [], "spent_inr": 0.0, "impact_people": 0, "population_reached": 0, "vulnerable_share": 0.0, "ward_counts": {}, "ward_coverage": 0}
    wards = sorted(frame.ward_key.unique()) if not frame.empty else []
    if len(wards) < wards_required:
        return {**empty, "status": "infeasible", "optimal": False, "message": f"Only {len(wards)} distinct city/wards are available; {wards_required} were requested."}
    cheapest = frame.groupby("ward_key").cost_inr.min().sort_values().head(wards_required).sum()
    if cheapest > budget + 1e-6:
        return {**empty, "status": "infeasible", "optimal": False, "message": "The budget cannot cover the cheapest pocket in each requested ward. Increase the budget or reduce ward coverage."}
    n, w = len(frame), len(wards)
    rows, lower, upper = [], [], []
    def constraint(values: dict[int, float], lo: float, hi: float) -> None:
        rows.append(csr_matrix(([float(v) for v in values.values()], ([0] * len(values), list(values))), shape=(1, n + w)))
        lower.append(lo); upper.append(hi)
    constraint({i: float(v / budget) for i, v in enumerate(frame.cost_inr)}, -np.inf, 1)
    constraint({i: float(v) - share for i, v in enumerate(frame.vulnerable)}, 0, np.inf)
    constraint({n + j: 1 for j in range(w)}, wards_required, np.inf)
    for j, ward in enumerate(wards):
        indexes = frame.index[frame.ward_key == ward].tolist()
        # y = 1 iff at least one pocket in the distinct ward is selected.
        constraint({**{i: 1 for i in indexes}, n + j: -1}, 0, np.inf)
        constraint({**{i: 1 for i in indexes}, n + j: -len(indexes)}, -np.inf, 0)
        if equal_ward:
            constraint({i: float(frame.loc[i, "cost_inr"] / budget) for i in indexes}, -np.inf, 1 / w)
    objective = np.r_[-frame.impact.to_numpy() / max(float(frame.impact.max()), 1), np.zeros(w)]
    result = milp(objective, integrality=np.ones(n + w), bounds=Bounds(np.zeros(n + w), np.ones(n + w)),
                  constraints=LinearConstraint(vstack(rows).tocsr(), np.asarray(lower), np.asarray(upper)),
                  options={"time_limit": seconds, "mip_rel_gap": .02})
    if result.x is None:
        return {**empty, "status": "infeasible" if result.status == 2 else "no_feasible_plan_found", "optimal": False,
                "message": "No plan meets the budget, ward coverage and vulnerable-share constraints." if result.status == 2 else "The solver did not find a feasible plan within its time limit. Try a larger budget or simpler constraints."}
    selected = frame.loc[result.x[:n] > .5].copy()
    spent = float(selected.cost_inr.sum())
    vulnerable = float(selected.vulnerable.mean()) if len(selected) else 0
    coverage = selected.ward_key.nunique()
    # Never publish a solver incumbent that violates the displayed constraints.
    if spent > budget + .01 or vulnerable + 1e-8 < share or coverage < wards_required:
        return {**empty, "status": "no_feasible_plan_found", "optimal": False, "message": "The solver result failed constraint validation; no plan has been published."}
    selected["cost_inr"] = selected.cost_inr.round(2)
    selected["impact"] = selected.impact.round(2)
    return {"status": "feasible", "optimal": result.status == 0, "message": "Constraints verified. Impact is a synthetic risk-weighted planning proxy.",
            "selected": selected[["pocket_id", "city", "ward", "priority_score", "cost_inr", "impact"]].to_dict("records"),
            "spent_inr": round(spent, 2), "impact_people": round(float(selected.impact.sum())),
            "population_reached": int(selected.population.sum()), "vulnerable_share": round(vulnerable, 6),
            "ward_counts": {str(k): int(v) for k, v in selected.groupby("ward_key").size().items()}, "ward_coverage": int(coverage)}


def optimise(pockets: pd.DataFrame, budget_inr: float, min_vulnerable_share: float = .25, min_wards: int = 3) -> dict[str, Any]:
    if not math.isfinite(budget_inr) or budget_inr <= 0 or not 0 <= min_vulnerable_share <= 1 or min_wards < 1:
        raise ValueError("Provide a positive budget, a vulnerable share between zero and one, and at least one ward")
    frame = _options(pockets)
    plan = _solve(frame, budget_inr, min_vulnerable_share, min_wards)
    baseline = _solve(frame, budget_inr, min_vulnerable_share, min_wards, equal_ward=True)
    points = []
    for fraction in [.25, .5, .75, 1.0]:
        current = plan if fraction == 1 else _solve(frame, budget_inr * fraction, min_vulnerable_share, min_wards, seconds=.5)
        points.append({"budget_inr": round(budget_inr * fraction), "spent_inr": current["spent_inr"], "impact_people": current["impact_people"] if current["status"] == "feasible" else None, "status": current["status"]})
    return {**plan, "solver": "SciPy / HiGHS integer optimisation", "budget_inr": budget_inr,
            "constraints": {"min_vulnerable_share": min_vulnerable_share, "min_wards": min_wards},
            "baseline": {**baseline, "method": "Equal budget cap per city/ward, using the same cost, impact, total budget, minimum coverage and vulnerable-share constraints."},
            "pareto": points, "impact_description": "Population × priority / 100; a planning proxy, not observed beneficiaries or cost savings."}


def pareto_frontier(pockets: pd.DataFrame, max_budget: float) -> list[dict]:
    return optimise(pockets, max_budget, min_wards=1)["pareto"]

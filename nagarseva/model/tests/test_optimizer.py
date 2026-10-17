import pandas as pd
from model.src.optimizer import optimise


def pockets():
    return pd.DataFrame({"pocket_id": list("abcdefg"), "city": ["A"] * 7, "ward": ["w1", "w1", "w1", "w2", "w2", "w2", "w3"],
                         "population": [100] * 6 + [100000], "structural_risk_score": [50] * 7, "priority_score": [90] * 7})


def test_plan_and_real_baseline_respect_constraints():
    result = optimise(pockets(), 10_000_000, min_vulnerable_share=.25, min_wards=2)
    assert result["status"] == "feasible"
    assert result["spent_inr"] <= 10_000_000
    assert result["vulnerable_share"] >= .25
    assert result["ward_coverage"] >= 2
    baseline = result["baseline"]
    assert baseline["status"] == "feasible"
    assert baseline["impact_people"] == round(sum(p["impact"] for p in baseline["selected"]))
    assert baseline["spent_inr"] <= 10_000_000
    for ward in ["w1", "w2", "w3"]:
        assert sum(p["cost_inr"] for p in baseline["selected"] if p["ward"] == ward) <= 10_000_000 / 3 + .01
    assert all(p["status"] != "feasible" or p["spent_inr"] <= p["budget_inr"] for p in result["pareto"])


def test_distinct_ward_constraint_does_not_count_pockets():
    result = optimise(pockets(), 10_000_000, min_wards=3)
    assert result["status"] == "infeasible"
    assert result["selected"] == []
    assert "budget" in result["message"].lower()


def test_unavailable_ward_and_vulnerable_constraints_are_reported():
    result = optimise(pockets(), 10_000_000, min_wards=4)
    assert result["status"] == "infeasible"
    assert "distinct" in result["message"]
    frame = pockets().iloc[:6].copy()
    frame["priority_score"] = 20
    result = optimise(frame, 10_000_000, min_vulnerable_share=.5, min_wards=1)
    assert result["status"] == "infeasible"
    assert result["selected"] == []

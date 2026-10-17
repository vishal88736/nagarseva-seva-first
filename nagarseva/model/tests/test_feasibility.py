from model.src.feasibility import simulate, sensitivity


def test_viable_project_has_positive_saleable_area():
    result = simulate({"land_area_sqm": 10_000, "fsi": 3, "eligible_households": 400})
    assert result["gross_built_up_area_sqft"] > result["free_rehab_area_sqft"]
    assert "verdict" in result
    assert len(sensitivity(result["inputs"])) == 5


def test_bad_inputs_are_rejected():
    try:
        simulate({"land_area_sqm": 0, "fsi": 2, "eligible_households": 10})
    except ValueError:
        pass
    else:
        raise AssertionError("zero land must be rejected")


def test_rehab_capacity_cannot_be_overridden_by_profitable_assumptions():
    result = simulate({"land_area_sqm": 100, "fsi": 1, "eligible_households": 100, "tdr_value_per_sqft": 100000})
    assert result["developer_profit_inr"] > 0
    assert result["physically_feasible"] is False
    assert result["rehab_area_shortfall_sqft"] > 0
    assert result["verdict"] == "Not viable"
    assert result["break_even_market_rate_per_sqft"] is None


def test_no_sales_has_no_market_break_even_rate():
    result = simulate({"land_area_sqm": 10000, "fsi": 3, "eligible_households": 400, "sales_share_pct": 0})
    assert result["physically_feasible"] is True
    assert result["break_even_market_rate_per_sqft"] is None

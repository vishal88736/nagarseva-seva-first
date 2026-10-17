"""Generate a realistic, deterministic NagarSeva demo dataset.

The generator deliberately uses plausible distributions and correlations rather
than pretending to reproduce a particular settlement. See model/data/README.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

SEED = 20261008
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "synthetic"

REGIONS = [
    ("Mumbai", "M Ward", 19.01, 72.88, 0.31),
    ("Mumbai", "L Ward", 19.06, 72.89, 0.15),
    ("Mumbai", "S Ward", 19.14, 72.94, 0.14),
    ("Thane", "Thane West", 19.22, 72.98, 0.14),
    ("Thane", "Thane East", 19.20, 73.02, 0.08),
    ("Kalyan", "Kalyan West", 19.24, 73.13, 0.07),
    ("Kalyan", "Kalyan East", 19.23, 73.14, 0.04),
    ("Ambarnath", "Ambarnath", 19.19, 73.19, 0.04),
    ("Ulhasnagar", "Ulhasnagar", 19.22, 73.16, 0.03),
]


def _clip(values: np.ndarray, low: float, high: float) -> np.ndarray:
    return np.clip(values, low, high)


def _missing(df: pd.DataFrame, columns: Iterable[str], rng: np.random.Generator, rate: float = 0.045) -> pd.DataFrame:
    """Inject missing values into measurement columns, never identifiers."""
    for col in columns:
        mask = rng.random(len(df)) < rate
        df.loc[mask, col] = np.nan
    return df


def _region_rows(n: int, rng: np.random.Generator) -> pd.DataFrame:
    probs = np.array([r[4] for r in REGIONS])
    probs /= probs.sum()
    indexes = rng.choice(len(REGIONS), size=n, p=probs)
    rows = []
    for i, idx in enumerate(indexes):
        city, ward, lat, lon, _ = REGIONS[idx]
        rows.append((city, ward, lat + rng.normal(0, 0.018), lon + rng.normal(0, 0.018)))
    return pd.DataFrame(rows, columns=["city", "ward", "base_lat", "base_lon"])


def make_pockets(rng: np.random.Generator, n: int = 1500) -> pd.DataFrame:
    regions = _region_rows(n, rng)
    area = _clip(rng.lognormal(np.log(18_000), 0.62, n), 2_500, 120_000)
    households = _clip((area / rng.uniform(23, 43, n)).astype(int), 70, 2_800)
    population = (households * rng.normal(4.45, 0.5, n)).astype(int)
    density = population / area * 10_000
    creek_distance = np.abs(rng.normal(2.1, 1.6, n))
    flood = _clip(74 - creek_distance * 13 + rng.normal(0, 13, n), 3, 99)
    kutcha = _clip(0.12 + flood / 230 + rng.normal(0, 0.09, n), 0.03, 0.78)
    income = _clip(22_000 - kutcha * 19_000 - flood * 35 + rng.normal(0, 4_800, n), 5_000, 48_000)
    land = rng.choice(["state", "private", "railway", "forest", "CRZ"], n, p=[.37, .35, .12, .08, .08])
    return pd.DataFrame({
        "pocket_id": [f"NS-{i:04d}" for i in range(1, n + 1)],
        "ward": regions.ward,
        "city": regions.city,
        "lat": regions.base_lat,
        "lon": regions.base_lon,
        "area_sqm": np.round(area, 1),
        "households": households,
        "population": population,
        "density_per_ha": np.round(density, 1),
        "avg_household_income_inr": np.round(income, -2),
        "pct_below_poverty": np.round(_clip(0.14 + kutcha * .72 + rng.normal(0, .06, n), .04, .94), 3),
        "pct_kutcha_houses": np.round(kutcha, 3),
        "pct_women_headed": np.round(_clip(rng.normal(.18, .07, n), .05, .46), 3),
        "pct_migrants": np.round(_clip(.21 + rng.normal(0, .14, n) + (regions.city == "Mumbai") * .08, .03, .86), 3),
        "land_ownership": land,
        "flood_risk_score": np.round(flood, 1),
        "fire_risk_score": np.round(_clip(26 + density / 12 + kutcha * 42 + rng.normal(0, 10, n), 4, 99), 1),
        "structural_risk_score": np.round(_clip(18 + kutcha * 71 + flood * .08 + rng.normal(0, 10, n), 2, 99), 1),
        "distance_to_transit_km": np.round(_clip(rng.gamma(1.8, .9, n), .05, 8), 2),
        "distance_to_hospital_km": np.round(_clip(rng.gamma(2.3, .9, n), .1, 12), 2),
        "distance_to_school_km": np.round(_clip(rng.gamma(2, .55, n), .05, 7), 2),
        "tenure_security_score": np.round(_clip(80 - (land == "railway") * 32 - (land == "forest") * 28 - (land == "private") * 8 + rng.normal(0, 12, n), 4, 98), 1),
        "years_since_settlement": rng.integers(3, 58, n),
    })


def make_services(pockets: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = len(pockets)
    flood = pockets.flood_risk_score.to_numpy()
    poverty = pockets.pct_below_poverty.to_numpy()
    pipes = _clip(.78 - poverty * .42 - flood / 370 + rng.normal(0, .1, n), .08, .99)
    open_def = _clip(.04 + (1 - pipes) * .34 + rng.normal(0, .035, n), 0, .7)
    return pd.DataFrame({
        "pocket_id": pockets.pocket_id,
        "water_hours_per_day": np.round(_clip(9.0 - poverty * 5.9 - flood / 33 + rng.normal(0, 1.4, n), .4, 20), 1),
        "pct_piped_water": np.round(pipes, 3),
        "water_quality_ph_tds_ecoli_flag": np.round(_clip(rng.normal(0.28, .2, n) + flood / 600, 0, 1), 3),
        "toilets_per_100_people": np.round(_clip(24 - poverty * 13 + rng.normal(0, 4, n), 5, 40), 1),
        "pct_open_defecation": np.round(open_def, 3),
        "sewer_connection_pct": np.round(_clip(pipes - .1 + rng.normal(0, .09, n), .02, .98), 3),
        "pct_electrified_legal": np.round(_clip(.9 - poverty * .32 + rng.normal(0, .07, n), .35, 1), 3),
        "outage_hours_per_week": np.round(_clip(3 + poverty * 12 + rng.normal(0, 3, n), .1, 38), 1),
        "waste_collection_frequency": np.round(_clip(6 - poverty * 3 + rng.normal(0, .9, n), 0, 7), 1),
        "drain_blockage_incidents": rng.poisson(2 + flood / 15, n),
        "clinic_within_1km": (pockets.distance_to_hospital_km < 1).astype(int),
        "anganwadi_within_500m": (pockets.distance_to_school_km < .8).astype(int),
    })


def make_grievances(pockets: pd.DataFrame, rng: np.random.Generator, n: int = 20_000) -> pd.DataFrame:
    categories = ["water", "sanitation", "power", "waste", "drainage", "health", "safety", "housing"]
    templates = {
        "water": ["Water comes only for one hour and is muddy", "Paani nahi aa raha, tank empty", "पानी गंदा है और सप्लाई बंद है"],
        "sanitation": ["The community toilet is locked and overflowing", "Toilet band hai, safai nahi hoti", "शौचालय की सफाई नहीं हुई"],
        "power": ["Illegal line trips every night", "Light baar baar jaati hai", "बिजली की तारें बहुत असुरक्षित हैं"],
        "waste": ["Garbage has not been collected for four days", "Kachra gaadi nahi aayi", "कचरा जमा है"],
        "drainage": ["Drain is blocked after rain", "Nala bhar gaya hai", "नाला जाम है और पानी घर में आ रहा है"],
        "health": ["Children have fever after the water contamination", "Clinic bahut door hai", "बच्चों को दस्त हो रहे हैं"],
        "safety": ["The lane is dark and unsafe for women", "Raat ko gali mein light nahi hai", "महिलाओं के लिए रास्ता सुरक्षित नहीं"],
        "housing": ["Survey for rehab has not happened", "SRA survey ka status batao", "पुनर्विकास का सर्वे अभी नहीं हुआ"],
    }
    cats = rng.choice(categories, n, p=[.2, .13, .1, .16, .14, .08, .1, .09])
    selected = pockets.iloc[rng.integers(0, len(pockets), n)].reset_index(drop=True)
    texts = [templates[c][rng.integers(0, 3)] for c in cats]
    severity = _clip(rng.normal(2.2, .85, n) + np.isin(cats, ["health", "safety"]) * .65, 1, 4).round().astype(int)
    return pd.DataFrame({
        "complaint_id": [f"GR-{i:06d}" for i in range(1, n + 1)],
        "pocket_id": selected.pocket_id,
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="37min"),
        "text": texts,
        "category": cats,
        "severity": severity,
        "resolved_days": np.round(_clip(rng.normal(5 + severity * 2.7, 4, n), .2, 48), 1),
        "resolved": rng.random(n) > (.11 + (severity == 4) * .1),
    })


def make_projects(rng: np.random.Generator, n: int = 400) -> pd.DataFrame:
    types = rng.choice(["in_situ_SRA", "upgrading", "relocation", "rental_housing"], n, p=[.42, .3, .18, .1])
    units = rng.integers(80, 2_600, n)
    cost = _clip(rng.normal(2_850, 520, n), 1_850, 4_500)
    risk = np.isin(types, ["relocation", "rental_housing"])
    regions = _region_rows(n, rng)
    return pd.DataFrame({
        "project_id": [f"PR-{i:04d}" for i in range(1, n + 1)], "intervention_type": types,
        "city": regions.city, "ward": regions.ward,
        "units": units, "carpet_area_sqft": rng.choice([269, 300, 323, 350, 400], n),
        "construction_cost_per_sqft": np.round(cost, 0), "land_value_per_sqm": np.round(_clip(rng.normal(46_000, 17_000, n), 15_000, 120_000), 0),
        "FSI": np.round(_clip(rng.normal(2.6, .65, n), 1.2, 5.5), 2), "cross_subsidy_ratio": np.round(_clip(rng.normal(.52, .15, n), .15, .9), 3),
        "completion_months": np.round(_clip(rng.normal(34 + risk * 7, 9, n), 16, 72), 0), "delay_months": np.round(_clip(rng.normal(8 + risk * 4, 7, n), 0, 38), 0),
        "cost_overrun_pct": np.round(_clip(rng.normal(12, 9, n), 0, 55), 1), "resident_satisfaction": np.round(_clip(rng.normal(.62, .17, n) - risk * .1, .1, .96), 3),
        "viability_flag": rng.random(n) > (.27 + risk * .12),
    })


def make_households(pockets: pd.DataFrame, rng: np.random.Generator, n: int = 10_000) -> pd.DataFrame:
    selected = pockets.iloc[rng.integers(0, len(pockets), n)].reset_index(drop=True)
    income = _clip(rng.lognormal(np.log(13_500), .55, n), 3_000, 90_000)
    family = rng.integers(1, 9, n)
    ration = rng.random(n) > .22
    aadhaar = rng.random(n) > .12
    tenure = rng.random(n) > .35
    return pd.DataFrame({
        "household_id": [f"HH-{i:05d}" for i in range(1, n + 1)], "pocket_id": selected.pocket_id,
        "monthly_income_inr": np.round(income, -2), "family_size": family,
        "documents_held": [", ".join(x) for x in zip(np.where(aadhaar, "aadhaar", "",), np.where(ration, "ration_card", "",), np.where(tenure, "address_proof", "",))],
        "pmay_clss_eligible": (income <= 50_000) & aadhaar, "sra_eligible": tenure & (selected.years_since_settlement >= 10),
        "rental_housing_eligible": income <= 25_000,
    })


def make_budgets(pockets: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    budgets = [25_000_000, 50_000_000, 100_000_000, 250_000_000, 500_000_000]
    return pd.DataFrame({"scenario_id": [f"B-{i+1}" for i in range(len(budgets))], "budget_inr": budgets,
                         "minimum_vulnerable_share": [.2, .25, .3, .35, .4], "minimum_wards": [3, 4, 5, 7, 8],
                         "objective": "people_served", "assumption": "Synthetic cost bands; validate with DPR rates"})


def make_geojson(pockets: pd.DataFrame) -> dict:
    features = []
    for row in pockets.itertuples():
        dlat = .0012 + min(row.area_sqm / 100_000_000, .001)
        dlon = dlat / max(np.cos(np.radians(row.lat)), .5)
        ring = [[row.lon - dlon, row.lat - dlat], [row.lon + dlon, row.lat - dlat], [row.lon + dlon, row.lat + dlat], [row.lon - dlon, row.lat + dlat], [row.lon - dlon, row.lat - dlat]]
        features.append({"type": "Feature", "properties": {"pocket_id": row.pocket_id, "city": row.city, "ward": row.ward}, "geometry": {"type": "Polygon", "coordinates": [ring]}})
    return {"type": "FeatureCollection", "features": features}


def load_real_data(source: str | None = None) -> pd.DataFrame:
    """Placeholder for licensed OGD/Census/OSM/MoHUA ingestion."""
    raise NotImplementedError(f"Real-data connector '{source or 'unspecified'}' is documented but not bundled.")


def load_data_gov_india() -> pd.DataFrame:
    return load_real_data("data.gov.in")


def load_census_of_india() -> pd.DataFrame:
    return load_real_data("Census of India")


def load_nfhs() -> pd.DataFrame:
    return load_real_data("NFHS-5")


def load_openstreetmap() -> pd.DataFrame:
    return load_real_data("OpenStreetMap")


def load_sentinel2() -> pd.DataFrame:
    return load_real_data("Sentinel-2")


def load_open_buildings() -> pd.DataFrame:
    return load_real_data("Google Open Buildings")


def load_worldpop() -> pd.DataFrame:
    return load_real_data("WorldPop")


def load_mohua_dashboards() -> pd.DataFrame:
    return load_real_data("MoHUA dashboards")


def load_bmc_tmc_open_data() -> pd.DataFrame:
    return load_real_data("BMC/TMC open data")


def generate(seed: int = SEED) -> None:
    rng = np.random.default_rng(seed)
    OUT.mkdir(parents=True, exist_ok=True)
    pockets = make_pockets(rng)
    services = make_services(pockets, rng)
    grievances = make_grievances(pockets, rng)
    projects = make_projects(rng)
    households = make_households(pockets, rng)
    budgets = make_budgets(pockets, rng)
    numeric = [c for c in pockets.columns if c not in {"pocket_id", "ward", "city", "land_ownership"}]
    _missing(pockets, numeric, rng)
    _missing(services, [c for c in services.columns if c != "pocket_id"], rng)
    named_tables = {
        "slum_pockets": pockets,
        "service_access": services,
        "grievances": grievances,
        "redevelopment_projects": projects,
        "households_sample": households,
        "budget_scenarios": budgets,
    }
    for name, df in named_tables.items():
        df.to_csv(OUT / f"{name}.csv", index=False)
    (OUT / "pockets.geojson").write_text(json.dumps(make_geojson(pockets)), encoding="utf-8")
    (OUT / "generation_manifest.json").write_text(json.dumps({"seed": seed, "synthetic": True, "rows": {"pockets": len(pockets), "services": len(services), "grievances": len(grievances), "projects": len(projects), "households": len(households)}}, indent=2), encoding="utf-8")
    print(f"Generated seeded synthetic data in {OUT} (seed={seed})")


if __name__ == "__main__":
    generate()

"""Transparent settlement scoring and hypothetical planning, without ML models.

The browser implements the same public calculations; shared fixtures test parity.
No function makes eligibility, engineering-safety or relocation decisions.
"""
from __future__ import annotations

import heapq
from copy import deepcopy
import json
import math
from pathlib import Path

KEYS = ("water", "sanitation", "housing", "access", "risk")
DEFAULT_WEIGHTS = dict(zip(KEYS, (.30, .25, .20, .15, .10)))
DATA_PATH = Path(__file__).resolve().parents[2] / "shared/urban-demo.json"


def dataset() -> dict:
    return json.loads(DATA_PATH.read_text())


def number(value, name: str, low=0, high=math.inf) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be finite and between {low} and {high}.")
    return float(value)


def normalize_weights(weights: dict) -> dict:
    if set(weights) != set(KEYS):
        raise ValueError("Supply exactly water, sanitation, housing, access and risk weights.")
    values = {key: number(weights[key], key, 0, 100) for key in KEYS}
    total = sum(values.values())
    if total <= 0:
        raise ValueError("At least one indicator must have a positive weight.")
    return {key: value / total for key, value in values.items()}


def score(indicators: dict, weights: dict | None = None) -> dict:
    if set(indicators) != set(KEYS):
        raise ValueError("Supply all five indicators; use null for unavailable values.")
    normalized = normalize_weights(DEFAULT_WEIGHTS if weights is None else weights)
    missing, contributions = [], {}
    for key in KEYS:
        value = indicators[key]
        if value is None:
            missing.append(key)
            contributions[key] = None
        else:
            contributions[key] = number(value, key, 0, 100) * normalized[key]
    lower = sum(value for value in contributions.values() if value is not None)
    missing_weight = sum(normalized[key] for key in missing)
    rankable = missing_weight <= 1e-12
    return {"score": round(lower, 6) if rankable else None,
            "lower": round(lower, 6), "upper": round(lower + 100 * missing_weight, 6),
            "coverage_pct": round(100 * (1 - missing_weight), 6),
            "rankable": rankable, "missing": missing, "weights": normalized,
            "contributions": {key: round(value, 6) if value is not None else None for key, value in contributions.items()}}


def prioritize(clusters: list[dict], weights: dict | None = None) -> dict:
    normalized = normalize_weights(DEFAULT_WEIGHTS if weights is None else weights)
    rows = [{"id": item["id"], "name": item["name"], **score(item["indicators"], normalized)} for item in clusters]
    baseline = {item["id"]: score(item["indicators"], {key: 1 for key in KEYS})["score"] for item in clusters}
    ranked = sorted((item for item in rows if item["rankable"]), key=lambda item: (-item["score"], item["id"]))
    for item in rows:
        item["rank"] = 1 + sum(other["score"] > item["score"] for other in ranked) if item["rankable"] else None
        value = baseline[item["id"]]
        item["baseline_score"] = value
        item["baseline_rank"] = 1 + sum(other is not None and other > value for other in baseline.values()) if value is not None else None
    ranked += sorted((item for item in rows if not item["rankable"]), key=lambda item: item["id"])
    comparable = [item for item in rows if item["rankable"] and item["baseline_score"] is not None]
    # Average ranks handle ties; Spearman is undefined for a constant ranking.
    def average_ranks(field):
        values = [item[field] for item in comparable]
        return [1 + sum(other > value for other in values) + (sum(other == value for other in values) - 1) / 2 for value in values]
    a, b = average_ranks("score"), average_ranks("baseline_score")
    mean_a = sum(a) / len(a) if a else 0
    mean_b = sum(b) / len(b) if b else 0
    denominator = math.sqrt(sum((x - mean_a) ** 2 for x in a) * sum((y - mean_b) ** 2 for y in b))
    rho = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b)) / denominator if denominator else None
    return {"weights": normalized, "items": ranked, "baseline": "Equal weights on the same supplied indicators; not an independent field baseline",
            "rank_correlation": round(rho, 6) if rho is not None else None,
            "comparable_clusters": len(comparable), "synthetic": all(item.get("synthetic", False) for item in clusters)}


def distance_m(a: dict, b: dict) -> float:
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    delta_lat, delta_lon = lat2 - lat1, math.radians(b["lon"] - a["lon"])
    hav = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 6_371_000 * 2 * math.asin(min(1, math.sqrt(hav)))


def network_access(data: dict, start: str) -> list[dict]:
    nodes = {node["id"]: node for node in data["network"]["nodes"]}
    graph = {node: [] for node in nodes}
    for edge in data["network"]["edges"]:
        if not edge.get("walkable", True):
            continue
        a, b = edge["from"], edge["to"]
        if a not in nodes or b not in nodes:
            raise ValueError("Network edge references an unknown node.")
        length = distance_m(nodes[a], nodes[b])
        graph[a].append((b, length))
        graph[b].append((a, length))
    distances, queue = ({start: 0}, [(0, start)]) if start in nodes else ({}, [])
    while queue:
        cost, node = heapq.heappop(queue)
        if cost > distances.get(node, math.inf):
            continue
        for other, length in graph[node]:
            candidate = cost + length
            if candidate < distances.get(other, math.inf):
                distances[other] = candidate
                heapq.heappush(queue, (candidate, other))
    return [{**amenity, "distance_m": round(distances[amenity["node_id"]], 1) if amenity["node_id"] in distances else None}
            for amenity in data["amenities"]]


def compare_scenarios(data: dict, cluster_id: str, assumptions: dict) -> dict:
    cluster = next((item for item in data["clusters"] if item["id"] == cluster_id), None)
    if cluster is None:
        raise ValueError("Unknown cluster.")
    households = assumptions.get("households")
    number(households, "Scenario households", 1, 100_000)
    if int(households) != households:
        raise ValueError("Scenario households must be a whole number, not an eligibility count.")
    contingency = number(assumptions["contingency_pct"], "Contingency", 0, 100)
    rent = number(assumptions["temporary_rent_per_month"], "Temporary rent", 0, 1_000_000)
    maintenance = number(assumptions["annual_maintenance_per_household"], "Maintenance", 0, 1_000_000)
    options = assumptions["options"]
    kinds = [item["kind"] for item in options]
    if len(kinds) != len(set(kinds)) or set(kinds) not in ({"upgrade", "redevelop"}, {"upgrade", "redevelop", "relocate"}):
        raise ValueError("Compare upgrading and in-situ redevelopment once each; relocation is optional.")
    include = assumptions.get("include_relocation", False)
    if ("relocate" in kinds) != include:
        raise ValueError("Relocation must be explicitly enabled and supplied as an option.")
    if include and len(assumptions.get("relocation_reason", "").strip()) < 10:
        raise ValueError("Explain the assumptions that justify comparing a relocation thought experiment.")
    before = network_access(data, cluster["node_id"])
    results = []
    for item in options:
        unit = number(item["unit_cost_inr"], "Unit cost", 0, 100_000_000)
        shared = number(item["shared_works_inr"], "Shared works", 0, 100_000_000_000)
        months = number(item["months"], "Implementation months", 1, 120)
        temporary = number(item["temporary_months"], "Temporary-support months", 0, months)
        share = number(item["disrupted_share"], "Disrupted household share", 0, 1)
        coverage = number(item["assumed_service_coverage_pct"], "Assumed service coverage", 0, 100)
        disrupted = math.ceil(households * share)
        support = disrupted * temporary * rent
        base = households * unit + shared
        after = network_access(data, data["relocation_node_id"] if item["kind"] == "relocate" else cluster["node_id"])
        results.append({**item, "households_assumed": households, "construction_and_shared_inr": round(base, 2),
                        "temporary_support_inr": round(support, 2), "total_cost_inr": round((base + support) * (1 + contingency / 100), 2),
                        "annual_maintenance_inr": round(households * maintenance, 2), "disrupted_households": disrupted,
                        "access": [{**end, "baseline_distance_m": start["distance_m"],
                                    "change_m": round(end["distance_m"] - start["distance_m"], 1) if end["distance_m"] is not None and start["distance_m"] is not None else None}
                                   for start, end in zip(before, after)], "assumed_service_coverage_pct": coverage})
    return {"cluster_id": cluster_id, "options": results, "assumptions": deepcopy(assumptions), "synthetic": True,
            "limits": "Hypothetical costs and coverage assumptions, not estimates from quotations. Distances use a synthetic graph. No engineering, financial, tenure or relocation approval is established."}

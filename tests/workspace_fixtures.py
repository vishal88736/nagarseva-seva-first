"""Synthetic contracts for software checks; never real service observations."""
from datetime import datetime, timedelta, timezone


def workspace_fixture():
    observed = datetime.now(timezone.utc) - timedelta(hours=1)
    def feature(identifier, name, lon, lat, households):
        return {"type": "Feature", "properties": {"id": identifier, "name": name, "administrative_area": "Test ward", "households": households},
                "geometry": {"type": "Polygon", "coordinates": [[[lon, lat], [lon+.002, lat], [lon+.002, lat+.002], [lon, lat+.002], [lon, lat]]]}}
    observations = [{"id": "FIX-"+key, "settlement_id": "TEST-A", "indicator_type": key, "value": value,
                     "unit": "deficit_0_100", "reference_year": observed.year, "observation_date": observed.isoformat(),
                     "geographic_resolution": "settlement", "source": "AUTOMATED FIXTURE ONLY", "verification_status": "field_verified",
                     "inspector_reference": "test-inspector", "reviewer_reference": "test-reviewer", "method": "Authored software regression; no real observations",
                     "evidence_reference": "https://example.test/synthetic-evidence"}
                    for key, value in zip(["water", "sanitation", "housing", "access", "risk"], [80, 60, 40, 20, 10])]
    return {"title": "Automated test workspace", "source": "SYNTHETIC SOFTWARE FIXTURE", "source_date": observed.date().isoformat(),
            "settlements": {"type": "FeatureCollection", "features": [feature("TEST-A", "Fixture Harbour", 72.93, 19.05, 120), feature("TEST-B", "Fixture Hill", 73.86, 18.52, None)]},
            "observations": observations,
            "projects": [{"id": "TEST-P1", "settlement_id": "TEST-A", "scheme_name": "Linked fixture scheme", "project_status": "in_progress"},
                         {"id": "TEST-P2", "settlement_id": None, "scheme_name": "Unlinked fixture scheme"}],
            "spatial": {"type": "FeatureCollection", "features": [{"type": "Feature", "id": "TEST-SCHOOL", "geometry": {"type": "Point", "coordinates": [72.931,19.051]}, "properties": {"category": "amenity", "name": "Fixture school"}}]}}

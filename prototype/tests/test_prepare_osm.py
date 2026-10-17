"""Converter checks using authored, explicitly non-field Overpass-shaped inputs."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("prepare_osm", Path(__file__).resolve().parents[1] / "scripts" / "prepare_osm.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConverterTests(unittest.TestCase):
    def test_source_node_ids_and_unknown_observation_time_are_preserved(self):
        raw = {"osm3s": {"timestamp_osm_base": "2026-10-12T10:00:00Z"}, "elements": [
            {"type": "way", "id": 11, "nodes": [1, 2], "tags": {"highway": "footway", "access": "yes"}, "geometry": [{"lon": 0, "lat": 0}, {"lon": 0.001, "lat": 0}]},
            {"type": "node", "id": 1, "lon": 0, "lat": 0, "tags": {"amenity": "toilets", "name": "Synthetic conversion fixture", "contact:phone": "not-to-be-copied"}},
        ]}
        result = module.convert(raw, "https://overpass-api.de/api/interpreter", "2026-10-17", "Converter test only")
        self.assertEqual(result["network"]["features"][0]["properties"]["node_ids"], ["1", "2"])
        self.assertIsNone(result["metadata"]["observed_at"])
        self.assertEqual(result["metadata"]["snapshot_at"], "2026-10-12T10:00:00Z")
        self.assertNotIn("contact:phone", result["amenities"]["features"][0]["properties"])
        self.assertEqual(result["areas"], [])

    def test_representative_way_centre_is_not_claimed_as_an_entrance(self):
        result = module.convert({"elements": [{"type": "way", "id": 2, "tags": {"amenity": "bus_station"}, "center": {"lon": 0.1, "lat": 0.1}}]}, "https://overpass-api.de/api/interpreter", "2026-10-17", "Test")
        feature = result["amenities"]["features"][0]
        self.assertIn("not a passenger/public entrance", feature["properties"]["location_type"])
        self.assertEqual(feature["properties"]["category"], "transport_stop")

    def test_credentials_and_non_iso_or_impossible_dates_are_rejected(self):
        for source, date in [("https://user:secret@example.org", "2026-10-17"), ("file:///etc/passwd", "2026-10-17"), ("https://example.org", "20261017"), ("https://example.org", "2026-02-30")]:
            with self.subTest(source=source, date=date), self.assertRaises(ValueError):
                module.convert({"elements": []}, source, date, "Test")


if __name__ == "__main__":
    unittest.main()

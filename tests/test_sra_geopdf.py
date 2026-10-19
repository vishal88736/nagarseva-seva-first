"""Coordinate tests for source georeferencing, never polygon extraction."""
from copy import deepcopy

import numpy as np
from pyproj import CRS, Transformer
import pytest

from ingest_sra_pdf import control_transform


def viewport():
    local = [[0, 1], [0, 0], [1, 0], [1, 1]]
    inverse = Transformer.from_crs(32643, 4326, always_xy=True)
    controls = []
    for x, y in local:
        lon, lat = inverse.transform(260000 + 32000*x, 2130000 - 44000*y)
        controls.extend([lat, lon])
    return {"/BBox": [40, 3200, 2340, 30], "/Measure": {"/Subtype": "/GEO", "/LPTS": list(np.asarray(local).flat),
            "/GPTS": controls, "/GCS": {"/WKT": CRS.from_epsg(32643).to_wkt()}}}


def test_geopdf_control_fit_uses_lat_lon_order_and_top_down_local_y():
    affine, crs, bounds, controls = control_transform(viewport(), 3370)
    assert crs.to_epsg() == 32643 and bounds == (40, 170, 2340, 3340)
    np.testing.assert_allclose(affine, [[32000, 0], [0, -44000], [260000, 2130000]], atol=1e-7)
    assert max(control["affine_fit_residual_m"] for control in controls) < 1e-7
    assert controls[0]["latitude"] < controls[1]["latitude"]


def test_geopdf_rounding_residual_is_reported_and_non_affine_controls_rejected():
    source = viewport()
    source["/Measure"]["/GPTS"] = [round(value, 5) for value in source["/Measure"]["/GPTS"]]
    _, _, _, controls = control_transform(source, 3370)
    assert 0 < max(control["affine_fit_residual_m"] for control in controls) < 2
    source["/Measure"]["/GPTS"][0] += .001
    with pytest.raises(ValueError, match="consistent affine"):
        control_transform(source, 3370)


@pytest.mark.parametrize("kind", ["wrong_crs", "coordinate_order", "local_controls", "wrong_subtype"])
def test_geopdf_refuses_changed_source_conventions(kind):
    source = deepcopy(viewport())
    measure = source["/Measure"]
    if kind == "wrong_crs":
        measure["/GCS"]["/WKT"] = CRS.from_epsg(3857).to_wkt()
    if kind == "coordinate_order":
        values = measure["/GPTS"]
        measure["/GPTS"] = [value for pair in zip(values[1::2], values[::2]) for value in pair]
    if kind == "local_controls":
        measure["/LPTS"][0] = .1
    if kind == "wrong_subtype":
        measure["/Subtype"] = "/RL"
    with pytest.raises(ValueError):
        control_transform(source, 3370)

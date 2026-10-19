"""Warp a bounded historical GeoPDF map for display, never settlement analysis.

The official map has ISO geospatial control points but its map contents are
rasterized. This preserves that cartographic source as an optional context layer;
it does not segment pixels, digitise boundaries or assign geometry to clusters.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import tempfile

import numpy as np
from pyproj import CRS, Transformer

from data_common import Downloader, DownloadError, META, PILOT_BBOX, PROCESSED, ROOT, inventory, utcnow, write_json
from inspect_sra_layers import PDF_URL


def control_transform(viewport, page_height):
    """Fit all ISO GeoPDF control points in the declared projected CRS.

    /GPTS is latitude, longitude per ISO GeoPDF; pyproj uses longitude, latitude.
    MuPDF page coordinates have y increasing downwards. The source /BBox lists
    top before bottom, so its y limits are normalised explicitly here.
    """
    measure = viewport["/Measure"]
    if str(measure["/Subtype"]) != "/GEO":
        raise ValueError("Expected ISO geospatial PDF measurement dictionary")
    crs = CRS.from_wkt(str(measure["/GCS"]["/WKT"]))
    if not crs.is_projected or crs.to_epsg() != 32643:
        raise ValueError("Source CRS changed; review source coordinate adapter")
    local = np.asarray(measure["/LPTS"], dtype=float).reshape(-1, 2)
    geographic = np.asarray(measure["/GPTS"], dtype=float).reshape(-1, 2)
    if local.shape != (4, 2) or geographic.shape != (4, 2) or not np.isfinite(local).all() or not np.isfinite(geographic).all():
        raise ValueError("Expected four finite paired GeoPDF controls")
    if set(map(tuple, local.tolist())) != {(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)}:
        raise ValueError("Unexpected local control extent; manual review required")
    if not ((geographic[:, 0] > 18).all() and (geographic[:, 0] < 20).all() and (geographic[:, 1] > 72).all() and (geographic[:, 1] < 74).all()):
        raise ValueError("GeoPDF controls outside Mumbai context or coordinate order changed")
    transform = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    projected = np.column_stack(transform.transform(geographic[:, 1], geographic[:, 0]))
    design = np.column_stack([local, np.ones(4)])
    coefficients, _, rank, _ = np.linalg.lstsq(design, projected, rcond=None)
    residuals = np.linalg.norm(design @ coefficients - projected, axis=1)
    if rank != 3 or max(residuals) > 2:
        raise ValueError("GeoPDF controls do not support a consistent affine transform within two metres")
    if coefficients[0, 0] <= 0 or coefficients[1, 1] >= 0 or abs(np.linalg.det(coefficients[:2])) < 1:
        raise ValueError("Unexpected source orientation or singular affine transform")
    x1, y1, x2, y2 = map(float, viewport["/BBox"])
    bounds = (min(x1, x2), page_height - max(y1, y2), max(x1, x2), page_height - min(y1, y2))
    if bounds[2] <= bounds[0] or bounds[3] <= bounds[1] or bounds[1] < 0:
        raise ValueError("Invalid GeoPDF viewport")
    controls = [{"local": list(map(float, local[i])), "latitude": float(geographic[i, 0]), "longitude": float(geographic[i, 1]),
                 "easting": float(projected[i, 0]), "northing": float(projected[i, 1]), "affine_fit_residual_m": float(residuals[i])} for i in range(4)]
    return coefficients, crs, bounds, controls


def build_overlay(source_path, request, bbox=PILOT_BBOX, output_width=1024):
    # Optional acquisition dependencies do not affect API runtime dependencies.
    import pymupdf
    from pypdf import PdfReader
    from PIL import Image
    from rasterio.transform import Affine, from_bounds
    from rasterio.warp import reproject, Resampling

    if not 256 <= output_width <= 2048:
        raise ValueError("Overlay width must be between 256 and 2048 pixels")
    west, south, east, north = map(float, bbox)
    if not (72.7 <= west < east <= 73.1 and 18.8 <= south < north <= 19.4):
        raise ValueError("Overlay clip must remain within the bounded Mumbai map context")
    if (east - west) * (north - south) > 0.01:
        raise ValueError("Overlay clip exceeds the acquisition pilot area limit")
    reader = PdfReader(str(source_path))
    if len(reader.pages) != 1:
        raise ValueError("Source map page count changed")
    source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_digest != request["sha256"]:
        raise ValueError("Source PDF checksum differs from its download manifest")
    page = reader.pages[0]
    if page.rotation or float(page.get("/UserUnit", 1)) != 1:
        raise ValueError("Source page rotation or user unit changed")
    viewports = page.get("/VP", [])
    if len(viewports) != 1:
        raise ValueError("Expected exactly one GeoPDF map viewport")
    coefficients, crs, map_box, controls = control_transform(viewports[0], float(page.mediabox.height))
    # Geographic clip corners and edge midpoints guard against nonlinear extent.
    edge = [(west, south), (west, north), (east, south), (east, north), ((west + east) / 2, south), ((west + east) / 2, north), (west, (south + north) / 2), (east, (south + north) / 2)]
    projected = np.column_stack(Transformer.from_crs(4326, crs, always_xy=True).transform(*zip(*edge)))
    local = (projected - coefficients[2]) @ np.linalg.inv(coefficients[:2])
    if np.min(local) < 0 or np.max(local) > 1:
        raise ValueError("Requested pilot clip falls outside the source map viewport")
    left, top, right, bottom = map_box
    map_width, map_height = right - left, bottom - top
    pdf_corners = local * [map_width, map_height] + [left, top]
    scale = 4.0  # Approx. 3.5 source metres/pixel; no image-based feature extraction.
    clip = pymupdf.Rect(float(pdf_corners[:, 0].min()) - 1, float(pdf_corners[:, 1].min()) - 1,
                        float(pdf_corners[:, 0].max()) + 1, float(pdf_corners[:, 1].max()) + 1)
    with pymupdf.open(str(source_path)) as document:
        map_page = document[0]
        if "GPS SURVEY 2024" not in map_page.get_text("text").upper():
            raise ValueError("Source map reference-year title changed; manual review required")
        pixmap = map_page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip, alpha=False, colorspace=pymupdf.csRGB)
        image_count = len(map_page.get_images())
        drawing_counts = {}
        for drawing in map_page.get_drawings(extended=True):
            drawing_counts[drawing["type"]] = drawing_counts.get(drawing["type"], 0) + 1
    source = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3).transpose(2, 0, 1)
    x0, y0 = pixmap.x / scale, pixmap.y / scale
    local_origin = np.asarray([(x0 - left) / map_width, (y0 - top) / map_height])
    origin = local_origin @ coefficients[:2] + coefficients[2]
    source_affine = Affine(coefficients[0, 0] / (map_width * scale), coefficients[1, 0] / (map_height * scale), origin[0],
                           coefficients[0, 1] / (map_width * scale), coefficients[1, 1] / (map_height * scale), origin[1])
    to_web = Transformer.from_crs(4326, 3857, always_xy=True)
    xwest, ysouth = to_web.transform(west, south)
    xeast, ynorth = to_web.transform(east, north)
    height = max(1, round(output_width * (ynorth - ysouth) / (xeast - xwest)))
    if height > 2048:
        raise ValueError("Output aspect ratio exceeds maximum overlay height")
    output_transform = from_bounds(xwest, ysouth, xeast, ynorth, output_width, height)
    destination = np.zeros((4, height, output_width), dtype=np.uint8)
    for band in range(4):
        input_band = source[band] if band < 3 else np.full((pixmap.height, pixmap.width), 255, dtype=np.uint8)
        reproject(input_band, destination[band], src_transform=source_affine, src_crs=crs,
                  dst_transform=output_transform, dst_crs="EPSG:3857", resampling=Resampling.bilinear if band < 3 else Resampling.nearest,
                  init_dest_nodata=True, dst_nodata=0, num_threads=1)
    if not np.all(destination[3] == 255):
        raise ValueError("Warp did not fully cover the bounded pilot; refusing a partial overlay")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    output = PROCESSED / "sra_pilot_overlay.png"
    with tempfile.NamedTemporaryFile(dir=PROCESSED, suffix=".png", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        Image.fromarray(destination.transpose(1, 2, 0)).save(temporary_path, format="PNG")
        with Image.open(temporary_path) as check:
            check.load()
            if check.size != (output_width, height) or check.mode != "RGBA":
                raise ValueError("Generated overlay image failed parse validation")
        os.replace(temporary_path, output)
    finally:
        temporary_path.unlink(missing_ok=True)
    metadata = {"title": "SRA GPS Survey 2024 historical map — cartographic context", "source_url": request["url"],
                "source_path": request["path"], "source_sha256": source_digest,
                "retrieved_at": request["retrieved_at"], "generated_at": utcnow(), "source_date": "2024", "reference_year": 2024,
                "source_date_basis": "GPS Survey 2024 map title; individual feature dates unknown", "source_crs": "EPSG:32643", "crs": "EPSG:3857",
                "bounds": [west, south, east, north], "bounds_3857": [xwest, ysouth, xeast, ynorth], "width": output_width, "height": height,
                "path": str(output.relative_to(ROOT)), "filename": output.name, "image_file": output.name,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "image_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "bytes": output.stat().st_size, "image_bytes": output.stat().st_size,
                "pixel_resolution_3857_m": [output_transform.a, -output_transform.e],
                "approximate_ground_resolution_m": [float(abs(output_transform.a) * np.cos(np.deg2rad((south+north)/2))), float(abs(output_transform.e) * np.cos(np.deg2rad((south+north)/2)))],
                "source_clip_pdf_points": list(clip), "source_viewport_pdf_points": list(map_box),
                "source_render_scale": scale, "source_render_pixels": [pixmap.width, pixmap.height], "source_pixel_affine_32643": list(source_affine)[:6],
                "controls": controls, "maximum_control_fit_residual_m": max(control["affine_fit_residual_m"] for control in controls),
                "control_point_residual_m": [control["affine_fit_residual_m"] for control in controls],
                "source_image_count": image_count, "source_vector_drawing_type_counts": drawing_counts,
                "method": "All four ISO GeoPDF controls transformed from WGS84 latitude/longitude to declared UTM43N; affine fit; bounded RGB map render; rasterio bilinear warp to Web Mercator image grid",
                "synthetic": False, "analysis_allowed": False, "settlement_geometry_count": 0, "licence": "Not established; retain locally pending SRA reuse permission review",
                "limitations": ["Historical cartographic raster, not settlement vector boundaries; no feature IDs attached to pixels",
                                "Do not use for boundary area, legal recognition, routing origins or cluster-to-facility measurement",
                                "Control-fit residual measures internal transform consistency, not surveyed ground accuracy; map scale and registration limits remain",
                                "Rasterized symbols, labels and administrative context remain as printed; no segmentation or digitization performed"]}
    write_json(PROCESSED / "sra_pilot_overlay.json", metadata)
    return metadata


def ingest(refresh=False):
    downloader = Downloader("sra", refresh)
    report = {"attempted_at": utcnow(), "errors": []}
    try:
        raw, request = downloader.fetch(PDF_URL, "cluster-map-document", suffix=".pdf")
        if not raw.startswith(b"%PDF-"):
            raise ValueError("Source map is not a PDF response")
        metadata = build_overlay(ROOT / request["path"], request)
        report["overlay"] = metadata
        inventory(dataset_name="SRA GPS Survey 2024 georeferenced pilot raster", publisher="SRA Mumbai / DSLR GIS Cell", source_url=PDF_URL,
                  retrieved_at=request["retrieved_at"], observation_date=metadata["source_date_basis"], publication_date="Unknown; PDF creation metadata 2024-05-30",
                  geography="Govandi bounded map context, not an administrative unit", resolution=f"Raster {metadata['width']}x{metadata['height']}; about {metadata['approximate_ground_resolution_m'][0]:.2f} m output grid",
                  format="Geospatial PDF -> bounded PNG EPSG:3857 with JSON georeference manifest", record_count=1,
                  fields=["bounds", "source_crs", "crs", "controls", "source_sha256", "sha256", "analysis_allowed"], licence=metadata["licence"], access_status="downloaded",
                  validation_status="Original PDF parsed; all four control points checked; CRS, clip, complete alpha coverage, PNG dimensions and checksums verified",
                  intended_use="Optional historical cartographic map display", limitations=metadata["limitations"])
    except (DownloadError, ValueError, KeyError, OSError, ImportError) as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        inventory(dataset_name="SRA GPS Survey 2024 georeferenced pilot raster", publisher="SRA Mumbai / DSLR GIS Cell", source_url=PDF_URL,
                  retrieved_at=utcnow(), access_status="failed", validation_status="No new overlay activated; prior processed files retained", limitations=report["errors"])
    finally:
        downloader.close()
    write_json(META / "sra_pdf_georeference.json", report)
    print("SRA cartographic raster:", report.get("overlay", {}).get("width", 0), "; errors:", report["errors"])
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    ingest(parser.parse_args().refresh)

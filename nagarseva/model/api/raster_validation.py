"""Checks for the optional cartographic source image, never a polygon dataset."""
import hashlib
import math
import re
import struct
from urllib.parse import urlsplit
import zlib


def png_dimensions(raw):
    if not raw.startswith(b"\x89PNG\r\n\x1a\n") or len(raw) > 10_000_000:
        raise ValueError("Expected a bounded PNG image")
    offset, dimensions, has_pixels = 8, None, False
    while offset + 12 <= len(raw):
        length = struct.unpack(">I", raw[offset:offset + 4])[0]
        kind = raw[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(raw):
            raise ValueError("Truncated PNG chunk")
        payload = raw[offset + 8:end - 4]
        if zlib.crc32(kind + payload) & 0xffffffff != struct.unpack(">I", raw[end - 4:end])[0]:
            raise ValueError("PNG checksum failed")
        if dimensions is None:
            if kind != b"IHDR" or length != 13:
                raise ValueError("PNG must start with its image header")
            dimensions = struct.unpack(">II", payload[:8])
            if any(not 0 < value <= 4096 for value in dimensions):
                raise ValueError("Unsupported raster image dimensions")
        elif kind == b"IHDR":
            raise ValueError("Duplicate PNG image header")
        has_pixels = has_pixels or kind == b"IDAT"
        if kind == b"IEND":
            if length or end != len(raw) or not has_pixels:
                raise ValueError("Invalid PNG image ending")
            return dimensions
        offset = end
    raise ValueError("Incomplete PNG image")


def validate_overlay(row, raw, expected_source_sha256=None, expected_bounds=None):
    if not isinstance(row, dict):
        raise ValueError("Historical raster metadata must be an object")
    try:
        width, height = png_dimensions(raw)
        bounds, residuals = row["bounds"], row["control_point_residual_m"]
        source = urlsplit(row["source_url"])
        if (row.get("image_file") != "sra_pilot_overlay.png" or row.get("analysis_allowed") is not False
                or row.get("crs") != "EPSG:3857" or row.get("source_date") != "2024"
                or type(row.get("width")) is not int or type(row.get("height")) is not int
                or (row["width"], row["height"]) != (width, height)
                or len(raw) != row["image_bytes"] or hashlib.sha256(raw).hexdigest() != row["image_sha256"]
                or not re.fullmatch(r"[a-f0-9]{64}", row["source_sha256"])
                or source.scheme != "https" or source.hostname not in {"media.sra.gov.in", "sra.gov.in", "www.sra.gov.in"}
                or source.username or source.password or len(bounds) != 4
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds)
                or not (-180 <= bounds[0] < bounds[2] <= 180 and -90 <= bounds[1] < bounds[3] <= 90)
                or len(residuals) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in residuals)):
            raise ValueError("Raster header, provenance, bounds or control-point checks failed")
        if expected_source_sha256 and row["source_sha256"] != expected_source_sha256:
            raise ValueError("Raster source differs from the active source map")
        if expected_bounds is not None and list(bounds) != list(expected_bounds):
            raise ValueError("Raster bounds differ from the active pilot extent")
    except (KeyError, TypeError, struct.error) as exc:
        raise ValueError("Incomplete historical raster metadata") from exc
    return row

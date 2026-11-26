"""Validate reviewed historical geometry and prepare the same layer for MapLibre and Atlas."""
from __future__ import annotations

import json
from html import escape
from math import asinh, isfinite, pi, radians, tan
from pathlib import Path

from scripts.motion_toolkit import verified_local

MAX_MERCATOR_LATITUDE = 85.05112878


def atlas_overlay(geojson, receipt, *, year):
    if type(year) is not int or not -5000 <= year <= 2100 or receipt.get("year") != year:
        raise ValueError("The asset must match the reviewed historical year.")
    path = verified_local(geojson, receipt, maximum_bytes=2_000_000)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or "crs" in data:
        raise ValueError("Expected WGS84 FeatureCollection.")
    features = data.get("features")
    if not isinstance(features, list) or not 1 <= len(features) <= 200:
        raise ValueError("Unsupported feature count.")
    raw_lines, atlas_lines = [], []
    total = 0
    for feature in features:
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if not isinstance(geometry, dict):
            raise ValueError("Expected boundary geometry.")
        kind, points = geometry.get("type"), geometry.get("coordinates")
        if kind not in {"LineString", "MultiLineString", "Polygon", "MultiPolygon"} or not isinstance(points, list):
            raise ValueError("Unsupported boundary geometry.")
        if kind == "MultiPolygon" and not all(isinstance(polygon, list) for polygon in points):
            raise ValueError("Invalid polygon collection.")
        collections = ([points] if kind == "LineString" else points if kind != "MultiPolygon"
                       else [ring for polygon in points for ring in polygon])
        for line in collections:
            if not isinstance(line, list) or len(line) < 2:
                raise ValueError("Invalid boundary line.")
            total += len(line)
            if total > 25_000:
                raise ValueError("Simplify the reviewed data before adding it to Atlas.")
            segment = []
            for coordinate in line:
                if (not isinstance(coordinate, list) or len(coordinate) != 2
                        or any(type(value) not in (float, int) or not isfinite(value) for value in coordinate)):
                    raise ValueError("Coordinates must be finite longitude and latitude.")
                lon, lat = coordinate
                if not -180 <= lon <= 180 or not -90 <= lat <= 90:
                    raise ValueError("Coordinate outside WGS84 bounds.")
                if segment and abs(lon - segment[-1][0]) > 180:
                    if len(segment) > 1:
                        raw_lines.append(segment)
                    segment = []
                segment.append([lon, max(-MAX_MERCATOR_LATITUDE, min(MAX_MERCATOR_LATITUDE, lat))])
            if len(segment) > 1:
                raw_lines.append(segment)
    if not raw_lines:
        raise ValueError("No drawable boundary after antimeridian split.")
    for line in raw_lines:
        atlas_lines.append([[round(lon / 180 * 6.5, 6), round(asinh(tan(radians(lat))) / pi * 6.5, 6)]
                            for lon, lat in line])
    data = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "MultiLineString", "coordinates": raw_lines}}
    ]}
    return {"style": {
        "version": 8, "sources": {"historical": {"type": "geojson", "data": data,
                                                 "attribution": escape(receipt["attribution"])}},
        "layers": [{"id": "reviewed-boundaries", "source": "historical", "type": "line",
                    "paint": {"line-color": "#f6dca5", "line-width": 2, "line-dasharray": [2, 2]}}]},
        "atlas": {"lines": atlas_lines, "year": year, "attribution": receipt["attribution"]},
        "source": receipt["source"], "license": receipt["license"], "sha256": receipt["sha256"]}


def read_atlas(geojson, receipt, year):
    path = Path(receipt)
    if path.stat().st_size > 8192:
        raise ValueError("Atlas receipt is too large.")
    atlas = atlas_overlay(geojson, json.loads(path.read_text(encoding="utf-8")), year=year)
    return atlas

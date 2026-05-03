import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"
DOCS = BASE / "docs"

FULL_TRACK = OUTPUT / "latest_hurricane_full_track.csv"
NEAR_TRACK = OUTPUT / "latest_hurricane_near_jamaica.csv"
FORECAST = OUTPUT / "forecast_track_48h.csv"
FORECAST_VALIDATION = OUTPUT / "forecast_validation_against_observed.csv"
IMPACT = OUTPUT / "impact_parish_scores.csv"
IMPACT_GEOJSON = OUTPUT / "impact_parish_scores.geojson"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_time(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def fmt_num(value, digits=2):
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def wind_category(wind_kt):
    if wind_kt is None:
        return "Unknown"
    if wind_kt >= 137:
        return "Category 5"
    if wind_kt >= 113:
        return "Category 4"
    if wind_kt >= 96:
        return "Category 3"
    if wind_kt >= 83:
        return "Category 2"
    if wind_kt >= 64:
        return "Category 1"
    if wind_kt >= 34:
        return "Tropical storm"
    return "Tropical depression"


def duration_hours(rows):
    if not rows:
        return 0
    start = parse_time(rows[0]["iso_time_utc"])
    end = parse_time(rows[-1]["iso_time_utc"])
    return (end - start).total_seconds() / 3600


def track_summary(rows):
    winds = [to_float(r.get("usa_wind_kt") or r.get("USA_WIND")) for r in rows]
    winds = [w for w in winds if w is not None]
    lats = [to_float(r.get("lat") or r.get("LAT")) for r in rows]
    lons = [to_float(r.get("lon") or r.get("LON")) for r in rows]
    lats = [v for v in lats if v is not None]
    lons = [v for v in lons if v is not None]
    peak_row = max(rows, key=lambda r: to_float(r.get("usa_wind_kt") or r.get("USA_WIND")) or -1)
    peak_wind = to_float(peak_row.get("usa_wind_kt") or peak_row.get("USA_WIND"))
    return {
        "count": len(rows),
        "start": rows[0]["iso_time_utc"],
        "end": rows[-1]["iso_time_utc"],
        "duration_hours": duration_hours(rows),
        "max_wind": max(winds) if winds else None,
        "mean_wind": sum(winds) / len(winds) if winds else None,
        "peak_time": peak_row["iso_time_utc"],
        "peak_lat": to_float(peak_row.get("lat") or peak_row.get("LAT")),
        "peak_lon": to_float(peak_row.get("lon") or peak_row.get("LON")),
        "peak_category": wind_category(peak_wind),
        "lat_range": (min(lats), max(lats)) if lats else (None, None),
        "lon_range": (min(lons), max(lons)) if lons else (None, None),
    }


def impact_summary(rows):
    sorted_rows = sorted(rows, key=lambda r: to_float(r["impact_index"]) or 0, reverse=True)
    counts = Counter(r["impact_category"] for r in rows)
    return sorted_rows, counts


def forecast_summary(rows):
    winds = [to_float(r["forecast_wind_kt"]) for r in rows]
    conf = [to_float(r["confidence_radius_km"]) for r in rows]
    return {
        "count": len(rows),
        "start": rows[0]["iso_time_utc"],
        "end": rows[-1]["iso_time_utc"],
        "first_hour": rows[0]["forecast_hour"],
        "last_hour": rows[-1]["forecast_hour"],
        "start_wind": winds[0],
        "end_wind": winds[-1],
        "start_conf": conf[0],
        "end_conf": conf[-1],
        "model": rows[0]["model"],
    }


def interpolate_observed(full_rows, target_epoch):
    normalized = []
    for row in full_rows:
        normalized.append(
            {
                "epoch": int(row["epoch_utc"]),
                "time": row["iso_time_utc"],
                "lat": to_float(row["lat"]),
                "lon": to_float(row["lon"]),
                "wind": to_float(row["usa_wind_kt"]),
            }
        )
    normalized.sort(key=lambda r: r["epoch"])

    if target_epoch < normalized[0]["epoch"] or target_epoch > normalized[-1]["epoch"]:
        return None

    for idx in range(1, len(normalized)):
        before = normalized[idx - 1]
        after = normalized[idx]
        if before["epoch"] <= target_epoch <= after["epoch"]:
            if before["epoch"] == after["epoch"]:
                return before
            frac = (target_epoch - before["epoch"]) / (after["epoch"] - before["epoch"])
            return {
                "epoch": target_epoch,
                "time": datetime.fromtimestamp(target_epoch, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "lat": before["lat"] + (after["lat"] - before["lat"]) * frac,
                "lon": before["lon"] + (after["lon"] - before["lon"]) * frac,
                "wind": before["wind"] + (after["wind"] - before["wind"]) * frac,
            }
    return None


def write_forecast_validation(full_rows, forecast_rows):
    validation = []
    for row in forecast_rows:
        observed = interpolate_observed(full_rows, int(row["epoch_utc"]))
        if observed is None:
            continue
        predicted_lat = to_float(row["lat"])
        predicted_lon = to_float(row["lon"])
        predicted_wind = to_float(row["forecast_wind_kt"])
        error_km = haversine_km(predicted_lat, predicted_lon, observed["lat"], observed["lon"])
        wind_error = predicted_wind - observed["wind"] if observed["wind"] is not None else None
        validation.append(
            {
                "forecast_hour": int(row["forecast_hour"]),
                "forecast_time_utc": row["iso_time_utc"],
                "predicted_lat": round(predicted_lat, 4),
                "predicted_lon": round(predicted_lon, 4),
                "observed_lat_interpolated": round(observed["lat"], 4),
                "observed_lon_interpolated": round(observed["lon"], 4),
                "track_error_km": round(error_km, 2),
                "predicted_wind_kt": round(predicted_wind, 1),
                "observed_wind_kt_interpolated": round(observed["wind"], 1),
                "wind_error_kt": round(wind_error, 1) if wind_error is not None else None,
            }
        )

    with FORECAST_VALIDATION.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(validation[0].keys()))
        writer.writeheader()
        writer.writerows(validation)
    return validation


def validation_summary(rows):
    errors = [to_float(r["track_error_km"]) for r in rows if to_float(r["track_error_km"]) is not None]
    wind_errors = [to_float(r["wind_error_kt"]) for r in rows if to_float(r["wind_error_kt"]) is not None]
    if not errors:
        return {}
    return {
        "count": len(errors),
        "mean_track_error": sum(errors) / len(errors),
        "max_track_error": max(errors),
        "first_track_error": errors[0],
        "last_track_error": errors[-1],
        "mean_abs_wind_error": sum(abs(v) for v in wind_errors) / len(wind_errors) if wind_errors else None,
        "last_wind_error": wind_errors[-1] if wind_errors else None,
    }


def markdown_table(rows):
    lines = [
        "| Rank | Parish | Impact index | Category | Nearest time UTC | Distance km | Wind kt |",
        "|---:|---|---:|---|---|---:|---:|",
    ]
    for idx, row in enumerate(rows, start=1):
        lines.append(
            "| "
            f"{idx} | {row['parish']} | {float(row['impact_index']):.2f} | "
            f"{row['impact_category']} | {row['nearest_track_time_utc']} | "
            f"{float(row['nearest_track_dist_km']):.2f} | {row['nearest_wind_kt']} |"
        )
    return "\n".join(lines)


def write_report(full_rows, near_rows, forecast_rows, impact_rows, validation_rows):
    full = track_summary(full_rows)
    near = track_summary(near_rows)
    forecast = forecast_summary(forecast_rows)
    validation = validation_summary(validation_rows)
    ranked, counts = impact_summary(impact_rows)

    category_lines = "\n".join(
        f"- {category}: {counts[category]} parish(es)"
        for category in ["Very High", "High", "Moderate", "Low", "Very Low"]
        if counts.get(category)
    )

    report = f"""# ArcGIS Data Analysis: Hurricane Melissa GIS Project

## Purpose

This document analyses the ArcGIS-ready outputs in the Jamaica hurricane GIS project before the research paper is expanded. The analysis covers the observed storm track, Jamaica-impact window, parish exposure layer, and the current 48-hour future forecast layer.

## Dataset Inventory

- Full observed storm track: `{FULL_TRACK.name}` ({len(full_rows)} records)
- Jamaica-window observed track: `{NEAR_TRACK.name}` ({len(near_rows)} records)
- Forecast track: `{FORECAST.name}` ({len(forecast_rows)} records)
- Parish impact table: `{IMPACT.name}` ({len(impact_rows)} parishes)
- Parish impact polygons: `{IMPACT_GEOJSON.name}`

## Observed Track Findings

The full storm track begins at **{full['start']} UTC** and ends at **{full['end']} UTC**, covering approximately **{fmt_num(full['duration_hours'], 1)} hours**. The maximum recorded wind in the full project track is **{fmt_num(full['max_wind'], 0)} kt**, reached near **{full['peak_time']} UTC** at approximately **{fmt_num(full['peak_lat'], 2)} N, {fmt_num(full['peak_lon'], 2)} W**. This corresponds to **{full['peak_category']}** intensity using Saffir-Simpson wind thresholds.

The Jamaica-focused track window begins at **{near['start']} UTC** and ends at **{near['end']} UTC**, covering approximately **{fmt_num(near['duration_hours'], 1)} hours**. Within this local analysis window, the peak wind is **{fmt_num(near['max_wind'], 0)} kt**, also classified as **{near['peak_category']}**.

## Parish Exposure Findings

The current GIS model estimates parish-level exposure using a distance-decayed wind proxy. It measures relative exposure to storm-force winds based on the distance from each parish centroid to observed storm positions. It does not measure confirmed losses, deaths, rainfall flooding, storm surge, or infrastructure damage.

Exposure category counts:

{category_lines}

## Ranked Parish Exposure

{markdown_table(ranked)}

## Forecast Layer Findings

The project includes a **{forecast['last_hour']}-hour** future forecast with **{len(forecast_rows)} points**, beginning at **{forecast['start']} UTC** and ending at **{forecast['end']} UTC**. The model is `{forecast['model']}`.

The forecast wind estimate decreases from **{fmt_num(forecast['start_wind'], 0)} kt** at the first forecast point to **{fmt_num(forecast['end_wind'], 0)} kt** at the final point. The confidence radius increases from **{fmt_num(forecast['start_conf'], 0)} km** to **{fmt_num(forecast['end_conf'], 0)} km**, which correctly communicates growing uncertainty over time.

## Animation Output

An interactive browser animation has been generated at:

`output/melissa_arcgis_animation.html`

This file shows:

- Jamaica parish polygons coloured by impact index.
- Observed Hurricane Melissa track.
- Current animated storm position.
- 48-hour forecast points and path.
- A time slider and play/pause controls.

## Forecast Validation Against Observed Track

Because the full IBTrACS track continues after the forecast origin, the simple 48-hour forecast can be compared with later observed storm positions. A validation table has been generated at:

`{FORECAST_VALIDATION.name}`

The forecast validation includes **{validation.get('count', 0)} matched forecast points**. The first forecast point has a track error of approximately **{fmt_num(validation.get('first_track_error'), 1)} km**. By the final 48-hour forecast point, track error grows to approximately **{fmt_num(validation.get('last_track_error'), 1)} km**. The mean track error across all matched forecast points is **{fmt_num(validation.get('mean_track_error'), 1)} km**, and the maximum error is **{fmt_num(validation.get('max_track_error'), 1)} km**.

This is an important finding for the research paper: the simple linear model is useful for showing how GIS forecast layers are built, but it is not strong enough for operational prediction over 24 to 48 hours. A research-grade forecast section should compare simple trend forecasts with official advisory forecasts, ensemble forecast cones, or historical analogue scenarios.

## Research Implications

The current ArcGIS data supports an academic first-stage exposure analysis. The strongest evidence comes from the parish impact ranking and the mapped relationship between storm track, wind intensity, and parish proximity. For a stronger research paper, the next step is to validate this exposure model against external damage evidence and add more layers.

Recommended next data layers:

- Population by parish or gridded population.
- Road network and bridge locations.
- Hospitals, emergency shelters, airports, ports, and power infrastructure.
- Digital elevation model for flood and landslide susceptibility.
- Rainfall totals and storm surge estimates.
- Official post-disaster impact or damage assessments.
- Official forecast advisory positions for forecast-error validation.

## Method Caveats

The current model is suitable for academic demonstration and planning analysis, but it should not be described as an official forecast or official damage assessment. The future forecast is a simple trend model. The impact index is a wind-distance proxy and should be interpreted as relative exposure.
"""
    path = DOCS / "ARCGIS_DATA_ANALYSIS.md"
    path.write_text(report, encoding="utf-8")
    return path


def write_animation(full_rows, forecast_rows):
    with IMPACT_GEOJSON.open("r", encoding="utf-8") as f:
        impact_geojson = json.load(f)

    jamaica_rows = [
        row
        for row in full_rows
        if 15.6 <= to_float(row["lat"]) <= 20.4 and -80.2 <= to_float(row["lon"]) <= -74.2
    ]
    observed = [
        {
            "time": r["iso_time_utc"],
            "lat": to_float(r["lat"]),
            "lon": to_float(r["lon"]),
            "wind": to_float(r["usa_wind_kt"]),
            "status": r.get("usa_status", ""),
        }
        for r in jamaica_rows
    ]
    origin = {
        "time": full_rows[0]["iso_time_utc"],
        "lat": to_float(full_rows[0]["lat"]),
        "lon": to_float(full_rows[0]["lon"]),
        "wind": to_float(full_rows[0]["usa_wind_kt"]),
        "status": full_rows[0].get("usa_status", ""),
    }
    forecast = [
        {
            "time": r["iso_time_utc"],
            "hour": int(r["forecast_hour"]),
            "lat": to_float(r["lat"]),
            "lon": to_float(r["lon"]),
            "wind": to_float(r["forecast_wind_kt"]),
            "confidence": to_float(r["confidence_radius_km"]),
        }
        for r in forecast_rows
    ]

    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hurricane Melissa Jamaica Impact Animation</title>
  <style>
    :root {
      --ink: #172026;
      --muted: #60707c;
      --panel: #ffffff;
      --coast: #f3f0e6;
      --water: #d9ecf2;
      --track: #1f6f8b;
      --forecast: #ad2f45;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: #edf5f7;
    }
    main {
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
    }
    #mapWrap {
      position: relative;
      min-height: 100vh;
      background: var(--water);
      overflow: hidden;
    }
    svg {
      width: 100%;
      height: 100vh;
      display: block;
    }
    aside {
      background: var(--panel);
      border-left: 1px solid #c9d8df;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    h1 {
      font-size: 20px;
      line-height: 1.2;
      margin: 0;
    }
    .meta {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .readout {
      border: 1px solid #d6e0e5;
      border-radius: 8px;
      padding: 12px;
      background: #f8fbfc;
      min-height: 108px;
      font-size: 14px;
      line-height: 1.5;
    }
    .controls {
      display: grid;
      gap: 10px;
    }
    button {
      border: 0;
      border-radius: 8px;
      background: #1f6f8b;
      color: #fff;
      padding: 11px 12px;
      font-size: 15px;
      cursor: pointer;
    }
    input[type="range"] { width: 100%; }
    .legend {
      display: grid;
      gap: 7px;
      font-size: 13px;
    }
    .legendRow {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .swatch {
      width: 18px;
      height: 12px;
      border: 1px solid #87939a;
    }
    .pathObserved {
      fill: none;
      stroke: var(--track);
      stroke-width: 2.5;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .pathForecast {
      fill: none;
      stroke: var(--forecast);
      stroke-width: 2.5;
      stroke-dasharray: 7 7;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .forecastPoint {
      fill: #fff;
      stroke: var(--forecast);
      stroke-width: 2;
    }
    .stormPoint {
      fill: #fff;
      stroke: #0f4f67;
      stroke-width: 4;
    }
    .stormHalo {
      fill: rgba(31, 111, 139, 0.18);
      stroke: rgba(31, 111, 139, 0.35);
      stroke-width: 1;
    }
    .stormBand {
      fill: none;
      stroke: rgba(15, 79, 103, 0.55);
      stroke-width: 3;
      stroke-linecap: round;
      pointer-events: none;
    }
    .activeTrail {
      fill: none;
      stroke: rgba(31, 111, 139, 0.42);
      stroke-width: 7;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .parish {
      stroke: #34444d;
      stroke-width: 0.7;
      vector-effect: non-scaling-stroke;
    }
    .label {
      font-size: 10px;
      fill: #24333b;
      pointer-events: none;
      text-anchor: middle;
      paint-order: stroke;
      stroke: rgba(255,255,255,0.78);
      stroke-width: 3px;
      stroke-linejoin: round;
    }
    .oceanLabel {
      fill: rgba(35, 72, 86, 0.48);
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0;
      pointer-events: none;
    }
    .trackCallout {
      font-size: 12px;
      font-weight: 700;
      fill: #21323a;
      pointer-events: none;
      paint-order: stroke;
      stroke: rgba(255,255,255,0.86);
      stroke-width: 4px;
      stroke-linejoin: round;
    }
    .trackCalloutSub {
      font-size: 10px;
      font-weight: 600;
      fill: #40545d;
      pointer-events: none;
      paint-order: stroke;
      stroke: rgba(255,255,255,0.86);
      stroke-width: 3px;
      stroke-linejoin: round;
    }
    .originBox {
      border: 1px solid #d6e0e5;
      border-radius: 8px;
      padding: 11px;
      background: #fff;
      font-size: 13px;
      line-height: 1.45;
    }
    @media (max-width: 840px) {
      main { grid-template-columns: 1fr; }
      #mapWrap { min-height: 68vh; }
      svg { height: 68vh; }
      aside { border-left: 0; border-top: 1px solid #c9d8df; }
    }
  </style>
</head>
<body>
<main>
  <section id="mapWrap">
    <svg id="map" viewBox="0 0 1000 720" role="img" aria-label="Animated GIS map of Hurricane Melissa near Jamaica"></svg>
  </section>
  <aside>
    <h1>Hurricane Melissa Jamaica Impact Animation</h1>
    <div class="meta">Jamaica-impact window, parish exposure layer, and 48-hour forecast from the project ArcGIS-ready outputs.</div>
    <div class="originBox" id="originBox"></div>
    <div class="readout" id="readout"></div>
    <div class="controls">
      <button id="play">Play</button>
      <input id="slider" type="range" min="0" max="0" value="0">
    </div>
    <div class="legend">
      <div class="legendRow"><span class="swatch" style="background:#7b1e2b"></span>Very High exposure</div>
      <div class="legendRow"><span class="swatch" style="background:#e07139"></span>High exposure</div>
      <div class="legendRow"><span class="swatch" style="background:#f2c94c"></span>Moderate exposure</div>
      <div class="legendRow"><span class="swatch" style="background:#8bc6a1"></span>Low exposure</div>
      <div class="legendRow"><span class="swatch" style="background:#dce8dc"></span>Very Low exposure</div>
      <div class="legendRow"><span class="swatch" style="background:#1f6f8b"></span>Observed storm movement</div>
      <div class="legendRow"><span class="swatch" style="background:#ad2f45"></span>48-hour model forecast track</div>
    </div>
    <div class="meta">The forecast is a simple trend model for research visualization, not an official meteorological forecast.</div>
  </aside>
</main>
<script>
const impactGeojson = __IMPACT__;
const observed = __OBSERVED__;
const forecast = __FORECAST__;
const origin = __ORIGIN__;

const svg = document.getElementById("map");
const slider = document.getElementById("slider");
const play = document.getElementById("play");
const readout = document.getElementById("readout");
const originBox = document.getElementById("originBox");
const W = 1000;
const H = 720;
const PAD = 70;
let timer = null;

const forecastFocus = forecast.filter(d => d.lat <= 21.8 && d.lon >= -76.4);
const allPoints = observed.concat(forecastFocus).map(d => [d.lon, d.lat]);
const polygonPoints = [];
for (const f of impactGeojson.features) collectCoords(f.geometry.coordinates, polygonPoints);
const coords = allPoints.concat(polygonPoints);
const minLon = Math.min(...coords.map(d => d[0])) - 0.25;
const maxLon = Math.max(...coords.map(d => d[0])) + 0.25;
const minLat = Math.min(...coords.map(d => d[1])) - 0.25;
const maxLat = Math.max(...coords.map(d => d[1])) + 0.25;

function collectCoords(coords, out) {
  if (typeof coords[0] === "number") {
    out.push(coords);
    return;
  }
  for (const item of coords) collectCoords(item, out);
}

function project(lon, lat) {
  const x = PAD + ((lon - minLon) / (maxLon - minLon)) * (W - PAD * 2);
  const y = H - PAD - ((lat - minLat) / (maxLat - minLat)) * (H - PAD * 2);
  return [x, y];
}

function pathFromPoints(points) {
  return points.map((d, i) => {
    const [x, y] = project(d.lon, d.lat);
    return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function polygonPath(coords) {
  if (typeof coords[0][0][0] === "number") {
    return coords.map(ring => ring.map((pt, i) => {
      const [x, y] = project(pt[0], pt[1]);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ") + " Z").join(" ");
  }
  return coords.map(poly => polygonPath(poly)).join(" ");
}

function colorFor(score) {
  if (score >= 90) return "#7b1e2b";
  if (score >= 65) return "#e07139";
  if (score >= 40) return "#f2c94c";
  if (score >= 20) return "#8bc6a1";
  return "#dce8dc";
}

function centroid(feature) {
  const points = [];
  collectCoords(feature.geometry.coordinates, points);
  const lon = points.reduce((s, p) => s + p[0], 0) / points.length;
  const lat = points.reduce((s, p) => s + p[1], 0) / points.length;
  return project(lon, lat);
}

function el(name, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  svg.appendChild(node);
  return node;
}

function group(attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", "g");
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  svg.appendChild(node);
  return node;
}

function child(parent, name, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  parent.appendChild(node);
  return node;
}

el("rect", {x: 0, y: 0, width: W, height: H, fill: "#d9ecf2"});

const [caribbeanX, caribbeanY] = project(-77.2, 17.05);
const caribbean = el("text", {x: caribbeanX, y: caribbeanY, class: "oceanLabel"});
caribbean.textContent = "Caribbean Sea";

const [atlanticX, atlanticY] = project(-74.55, 21.35);
const atlantic = el("text", {x: atlanticX, y: atlanticY, class: "oceanLabel"});
atlantic.textContent = "Atlantic Ocean";

for (const feature of impactGeojson.features) {
  const score = Number(feature.properties.impact_index || 0);
  el("path", {
    d: polygonPath(feature.geometry.coordinates),
    class: "parish",
    fill: colorFor(score),
    opacity: "0.88"
  });
}

originBox.innerHTML = `
  <strong>Storm origin</strong><br>
  ${origin.time} UTC<br>
  ${origin.lat.toFixed(2)} N, ${origin.lon.toFixed(2)} W<br>
  Wind: ${origin.wind || "n/a"} kt, Status: ${origin.status || "n/a"}
`;

for (const feature of impactGeojson.features) {
  const [x, y] = centroid(feature);
  const name = feature.properties.parish || feature.properties.shapeName || "";
  if (name.length <= 16) {
    const text = el("text", {x, y, class: "label"});
    text.textContent = name;
  }
}

el("path", {d: pathFromPoints(observed), class: "pathObserved"});
el("path", {d: pathFromPoints(forecastFocus), class: "pathForecast"});

const observedCalloutAnchor = observed[Math.max(0, observed.length - 5)];
const [obsCalloutX, obsCalloutY] = project(observedCalloutAnchor.lon, observedCalloutAnchor.lat);
const observedCallout = el("text", {x: obsCalloutX + 18, y: obsCalloutY - 12, class: "trackCallout"});
observedCallout.textContent = "Observed storm movement";

if (forecastFocus.length) {
  const forecastCalloutAnchor = forecastFocus[Math.min(2, forecastFocus.length - 1)];
  const [fcCalloutX, fcCalloutY] = project(forecastCalloutAnchor.lon, forecastCalloutAnchor.lat);
  const labelX = Math.max(28, Math.min(W - 250, fcCalloutX - 155));
  const labelY = Math.max(34, fcCalloutY - 18);
  const forecastCallout = el("text", {x: labelX, y: labelY, class: "trackCallout"});
  forecastCallout.textContent = "Forecast track (model)";
  const forecastSub = el("text", {x: labelX, y: labelY + 16, class: "trackCalloutSub"});
  forecastSub.textContent = "dashed red; not official";
}

for (const f of forecastFocus) {
  const [x, y] = project(f.lon, f.lat);
  el("circle", {cx: x, cy: y, r: 4, class: "forecastPoint"});
}

const halo = el("circle", {cx: 0, cy: 0, r: 20, class: "stormHalo"});
const activeTrail = el("path", {d: "", class: "activeTrail"});
const bandA = el("path", {d: "", class: "stormBand"});
const bandB = el("path", {d: "", class: "stormBand"});
const storm = el("circle", {cx: 0, cy: 0, r: 8, class: "stormPoint"});

slider.max = observed.length - 1;

function update(idx) {
  const d = observed[idx];
  const [x, y] = project(d.lon, d.lat);
  const wind = Number(d.wind || 0);
  const radius = Math.max(14, Math.min(58, wind / 2.7));
  const angle = idx * 0.55;
  halo.setAttribute("cx", x);
  halo.setAttribute("cy", y);
  halo.setAttribute("r", radius);
  activeTrail.setAttribute("d", pathFromPoints(observed.slice(0, idx + 1)));
  bandA.setAttribute("d", spiralPath(x, y, radius * 0.18, radius * 0.88, angle));
  bandB.setAttribute("d", spiralPath(x, y, radius * 0.18, radius * 0.88, angle + Math.PI));
  storm.setAttribute("cx", x);
  storm.setAttribute("cy", y);
  readout.innerHTML = `
    <strong>${d.time} UTC</strong><br>
    Position: ${d.lat.toFixed(2)} N, ${d.lon.toFixed(2)} W<br>
    Wind: ${d.wind || "n/a"} kt<br>
    Status: ${d.status || "n/a"}
  `;
  slider.value = idx;
}

function spiralPath(cx, cy, inner, outer, angle) {
  const points = [];
  for (let i = 0; i <= 18; i++) {
    const t = i / 18;
    const r = inner + (outer - inner) * t;
    const a = angle + t * Math.PI * 1.25;
    points.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]);
  }
  return points.map((pt, i) => `${i ? "L" : "M"}${pt[0].toFixed(1)},${pt[1].toFixed(1)}`).join(" ");
}

function step() {
  const next = Number(slider.value) + 1;
  update(next >= observed.length ? 0 : next);
}

play.addEventListener("click", () => {
  if (timer) {
    clearInterval(timer);
    timer = null;
    play.textContent = "Play";
  } else {
    timer = setInterval(step, 450);
    play.textContent = "Pause";
  }
});

slider.addEventListener("input", () => update(Number(slider.value)));
update(0);
</script>
</body>
</html>
"""
    html = html.replace("__IMPACT__", json.dumps(impact_geojson))
    html = html.replace("__OBSERVED__", json.dumps(observed))
    html = html.replace("__FORECAST__", json.dumps(forecast))
    html = html.replace("__ORIGIN__", json.dumps(origin))
    path = OUTPUT / "melissa_arcgis_animation.html"
    path.write_text(html, encoding="utf-8")
    return path


def main():
    full_rows = read_csv(FULL_TRACK)
    near_rows = read_csv(NEAR_TRACK)
    forecast_rows = read_csv(FORECAST)
    impact_rows = read_csv(IMPACT)

    validation_rows = write_forecast_validation(full_rows, forecast_rows)
    report = write_report(full_rows, near_rows, forecast_rows, impact_rows, validation_rows)
    animation = write_animation(full_rows, forecast_rows)

    print(f"Wrote {FORECAST_VALIDATION}")
    print(f"Wrote {report}")
    print(f"Wrote {animation}")


if __name__ == "__main__":
    main()

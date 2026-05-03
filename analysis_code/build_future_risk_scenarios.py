import csv
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OUTPUT = BASE / "output"
DOCS = BASE / "docs"

TRACK_CSV = OUTPUT / "latest_hurricane_full_track.csv"
ADM1_GEOJSON = DATA / "geoBoundaries-JAM-ADM1.geojson"

SCENARIO_CSV = OUTPUT / "future_hurricane_scenario_parish_risk.csv"
SCENARIO_GEOJSON = OUTPUT / "future_hurricane_scenario_parish_risk.geojson"
SCENARIO_HTML = OUTPUT / "future_hurricane_scenario_explorer.html"
SCENARIO_DOC = DOCS / "FUTURE_FORECAST_SCENARIOS.md"


SCENARIOS = [
    {
        "scenario": "S1_melissa_repeat_corridor",
        "label": "Melissa-like repeat corridor",
        "lon_shift_deg": 0.0,
        "lat_shift_deg": 0.0,
        "wind_factor": 1.0,
        "description": "A future storm follows a similar Jamaica corridor and reaches similar peak intensity.",
    },
    {
        "scenario": "S2_west_shift_cat5",
        "label": "50 km west-shifted Category 5 corridor",
        "lon_shift_deg": -0.48,
        "lat_shift_deg": 0.0,
        "wind_factor": 1.0,
        "description": "A future Category 5 storm tracks about 50 km farther west, increasing exposure in western parishes.",
    },
    {
        "scenario": "S3_east_shift_cat5",
        "label": "50 km east-shifted Category 5 corridor",
        "lon_shift_deg": 0.48,
        "lat_shift_deg": 0.0,
        "wind_factor": 1.0,
        "description": "A future Category 5 storm tracks about 50 km farther east, increasing exposure toward central and eastern parishes.",
    },
    {
        "scenario": "S4_melissa_corridor_cat4",
        "label": "Melissa corridor with Category 4 intensity",
        "lon_shift_deg": 0.0,
        "lat_shift_deg": 0.0,
        "wind_factor": 0.82,
        "description": "A future storm follows a similar corridor but with lower Category 4 intensity.",
    },
    {
        "scenario": "S5_south_shift_cat5",
        "label": "35 km south-shifted Category 5 corridor",
        "lon_shift_deg": 0.0,
        "lat_shift_deg": -0.32,
        "wind_factor": 1.0,
        "description": "A future Category 5 storm tracks slightly farther south, emphasizing southern coastal exposure.",
    },
]


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def polygon_centroid(poly_coords):
    ring = poly_coords[0]
    xs = [pt[0] for pt in ring]
    ys = [pt[1] for pt in ring]
    return sum(ys) / len(ys), sum(xs) / len(xs)


def geometry_centroid(geom):
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])
    if gtype == "Polygon":
        return polygon_centroid(coords)
    if gtype == "MultiPolygon":
        cents = [polygon_centroid(poly) for poly in coords]
        return sum(c[0] for c in cents) / len(cents), sum(c[1] for c in cents) / len(cents)
    raise ValueError(f"Unsupported geometry type: {gtype}")


def risk_category(score):
    if score >= 90:
        return "Extreme"
    if score >= 70:
        return "Very High"
    if score >= 50:
        return "High"
    if score >= 30:
        return "Moderate"
    return "Lower"


def read_track():
    with TRACK_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    jamaica_window = []
    for row in rows:
        lat = to_float(row["lat"])
        lon = to_float(row["lon"])
        wind = to_int(row.get("usa_wind_kt")) or to_int(row.get("wmo_wind_kt")) or 35
        if 16.0 <= lat <= 20.0 and -80.0 <= lon <= -74.5:
            jamaica_window.append(
                {
                    "time": row["iso_time_utc"],
                    "lat": lat,
                    "lon": lon,
                    "wind": wind,
                }
            )
    return jamaica_window


def score_parish(c_lat, c_lon, track, scenario):
    peak_score = -1.0
    peak = None
    for point in track:
        lat = point["lat"] + scenario["lat_shift_deg"]
        lon = point["lon"] + scenario["lon_shift_deg"]
        wind = point["wind"] * scenario["wind_factor"]
        distance = haversine_km(c_lat, c_lon, lat, lon)
        score = wind * math.exp(-distance / 80.0)
        if score > peak_score:
            peak_score = score
            peak = {
                "nearest_time_utc": point["time"],
                "nearest_lat": lat,
                "nearest_lon": lon,
                "nearest_dist_km": distance,
                "nearest_wind_kt": wind,
            }
    risk_index = min(100.0, peak_score * 1.3)
    return risk_index, peak


def main():
    track = read_track()
    with ADM1_GEOJSON.open("r", encoding="utf-8") as f:
        adm1 = json.load(f)

    rows = []
    scenario_scores_by_parish = {}

    for feature in adm1["features"]:
        props = feature.get("properties", {})
        parish = props.get("shapeName") or props.get("name") or props.get("shapeISO") or "UNKNOWN"
        c_lat, c_lon = geometry_centroid(feature["geometry"])
        parish_scores = []

        for scenario in SCENARIOS:
            risk_index, peak = score_parish(c_lat, c_lon, track, scenario)
            row = {
                "scenario": scenario["scenario"],
                "scenario_label": scenario["label"],
                "parish": parish,
                "centroid_lat": round(c_lat, 5),
                "centroid_lon": round(c_lon, 5),
                "future_risk_index": round(risk_index, 2),
                "future_risk_category": risk_category(risk_index),
                "nearest_track_time_utc": peak["nearest_time_utc"],
                "nearest_track_dist_km": round(peak["nearest_dist_km"], 2),
                "scenario_wind_kt": round(peak["nearest_wind_kt"], 1),
                "method": "scenario_distance_decay_wind_proxy",
            }
            rows.append(row)
            parish_scores.append(risk_index)

        scenario_scores_by_parish[parish] = {
            "max_future_risk_index": round(max(parish_scores), 2),
            "mean_future_risk_index": round(sum(parish_scores) / len(parish_scores), 2),
            "max_future_risk_category": risk_category(max(parish_scores)),
        }

    rows.sort(key=lambda r: (r["scenario"], -r["future_risk_index"]))

    with SCENARIO_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    features = []
    for feature in adm1["features"]:
        props = dict(feature.get("properties", {}))
        parish = props.get("shapeName") or props.get("name") or props.get("shapeISO") or "UNKNOWN"
        props.update(scenario_scores_by_parish[parish])
        props["scenario_set"] = "five_corridor_intensity_scenarios"
        features.append({"type": "Feature", "geometry": feature["geometry"], "properties": props})

    scenario_geojson = {
        "type": "FeatureCollection",
        "name": "future_hurricane_scenario_parish_risk",
        "features": features,
    }
    SCENARIO_GEOJSON.write_text(json.dumps(scenario_geojson), encoding="utf-8")
    write_scenario_explorer(adm1, rows)

    top_overall = sorted(
        scenario_scores_by_parish.items(),
        key=lambda item: item[1]["max_future_risk_index"],
        reverse=True,
    )

    table = "\n".join(
        "| "
        f"{idx} | {parish} | {values['max_future_risk_index']:.2f} | "
        f"{values['max_future_risk_category']} | {values['mean_future_risk_index']:.2f} |"
        for idx, (parish, values) in enumerate(top_overall, start=1)
    )

    scenario_list = "\n".join(f"- **{s['label']}**: {s['description']}" for s in SCENARIOS)

    doc = f"""# Future Hurricane Forecast Scenarios

## Purpose

This output adds a future-looking scenario forecast layer to the Hurricane Melissa GIS project. It does not claim to predict the exact next hurricane. Instead, it tests plausible future storm corridors and intensities using the Melissa Jamaica-impact corridor as a reference.

## Scenario Set

{scenario_list}

## Method

Each future scenario shifts or rescales the observed Melissa Jamaica-impact track. Parish centroids are scored using the same distance-decayed wind exposure method as the existing impact model:

`future risk score = scenario wind speed x exp(-distance / 80)`

The score is scaled to a 0-100 index and classified as Lower, Moderate, High, Very High, or Extreme.

## Overall Parish Risk Ranking Across Scenarios

| Rank | Parish | Maximum future risk index | Maximum category | Mean scenario risk index |
|---:|---|---:|---|---:|
{table}

## Generated Files

- `{SCENARIO_CSV.name}`: parish-by-scenario risk table.
- `{SCENARIO_GEOJSON.name}`: parish polygons with maximum and mean future scenario risk.
- `{SCENARIO_HTML.name}`: interactive browser map for comparing future scenarios.

## Research Use

This scenario layer is better for academic forecasting than a single deterministic prediction. It allows the research paper to discuss how Jamaica's parish-level risk changes when a future storm follows a similar, western-shifted, eastern-shifted, weaker, or south-shifted corridor.

## Caveats

These scenarios are not official forecasts. They do not include rainfall, storm surge, tide level, river flooding, slope failure, housing vulnerability, infrastructure fragility, or emergency response capacity. They should be described as exploratory spatial risk scenarios for preparedness planning.
"""
    SCENARIO_DOC.write_text(doc, encoding="utf-8")

    print(f"Wrote {SCENARIO_CSV}")
    print(f"Wrote {SCENARIO_GEOJSON}")
    print(f"Wrote {SCENARIO_HTML}")
    print(f"Wrote {SCENARIO_DOC}")


def write_scenario_explorer(adm1, rows):
    scores = {}
    labels = {}
    for row in rows:
        scenario = row["scenario"]
        labels[scenario] = row["scenario_label"]
        scores.setdefault(scenario, {})[row["parish"]] = {
            "risk": row["future_risk_index"],
            "category": row["future_risk_category"],
            "distance": row["nearest_track_dist_km"],
            "wind": row["scenario_wind_kt"],
        }

    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Future Hurricane Scenario Explorer</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: #172026;
      background: #d9ecf2;
    }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 340px;
      min-height: 100vh;
    }
    svg {
      width: 100%;
      height: 100vh;
      display: block;
    }
    aside {
      background: #fff;
      border-left: 1px solid #c7d8dd;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    h1 {
      font-size: 20px;
      margin: 0;
      line-height: 1.2;
    }
    select {
      width: 100%;
      border: 1px solid #aebdc4;
      border-radius: 8px;
      padding: 10px;
      font-size: 15px;
      background: #fff;
    }
    .readout {
      min-height: 130px;
      border: 1px solid #d6e0e5;
      border-radius: 8px;
      background: #f8fbfc;
      padding: 12px;
      font-size: 14px;
      line-height: 1.5;
    }
    .meta {
      color: #60707c;
      font-size: 13px;
      line-height: 1.45;
    }
    .parish {
      stroke: #34444d;
      stroke-width: 0.7;
      cursor: pointer;
      vector-effect: non-scaling-stroke;
    }
    .parish:hover {
      stroke: #111;
      stroke-width: 1.8;
    }
    .label {
      font-size: 10px;
      fill: #26363e;
      text-anchor: middle;
      pointer-events: none;
    }
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
    @media (max-width: 840px) {
      main { grid-template-columns: 1fr; }
      svg { height: 68vh; }
      aside { border-left: 0; border-top: 1px solid #c7d8dd; }
    }
  </style>
</head>
<body>
<main>
  <svg id="map" viewBox="0 0 1000 720" role="img" aria-label="Future hurricane scenario map for Jamaica"></svg>
  <aside>
    <h1>Future Hurricane Scenario Explorer</h1>
    <div class="meta">Compare parish-level risk across plausible future hurricane corridors based on the Melissa Jamaica-impact track.</div>
    <select id="scenario"></select>
    <div class="readout" id="readout">Select or hover over a parish.</div>
    <div class="legend">
      <div class="legendRow"><span class="swatch" style="background:#6f1724"></span>Extreme</div>
      <div class="legendRow"><span class="swatch" style="background:#c7432f"></span>Very High</div>
      <div class="legendRow"><span class="swatch" style="background:#e59a3b"></span>High</div>
      <div class="legendRow"><span class="swatch" style="background:#f2d36b"></span>Moderate</div>
      <div class="legendRow"><span class="swatch" style="background:#9fc7b3"></span>Lower</div>
    </div>
    <div class="meta">These are exploratory planning scenarios, not official hurricane forecasts.</div>
  </aside>
</main>
<script>
const adm1 = __ADM1__;
const scores = __SCORES__;
const labels = __LABELS__;
const svg = document.getElementById("map");
const scenarioSelect = document.getElementById("scenario");
const readout = document.getElementById("readout");
const W = 1000;
const H = 720;
const PAD = 70;

const polygonPoints = [];
for (const f of adm1.features) collectCoords(f.geometry.coordinates, polygonPoints);
const minLon = Math.min(...polygonPoints.map(d => d[0])) - 0.15;
const maxLon = Math.max(...polygonPoints.map(d => d[0])) + 0.15;
const minLat = Math.min(...polygonPoints.map(d => d[1])) - 0.15;
const maxLat = Math.max(...polygonPoints.map(d => d[1])) + 0.15;
const paths = [];

for (const [id, label] of Object.entries(labels)) {
  const option = document.createElement("option");
  option.value = id;
  option.textContent = label;
  scenarioSelect.appendChild(option);
}

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

function polygonPath(coords) {
  if (typeof coords[0][0][0] === "number") {
    return coords.map(ring => ring.map((pt, i) => {
      const [x, y] = project(pt[0], pt[1]);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ") + " Z").join(" ");
  }
  return coords.map(poly => polygonPath(poly)).join(" ");
}

function centroid(feature) {
  const points = [];
  collectCoords(feature.geometry.coordinates, points);
  const lon = points.reduce((s, p) => s + p[0], 0) / points.length;
  const lat = points.reduce((s, p) => s + p[1], 0) / points.length;
  return project(lon, lat);
}

function colorFor(category) {
  if (category === "Extreme") return "#6f1724";
  if (category === "Very High") return "#c7432f";
  if (category === "High") return "#e59a3b";
  if (category === "Moderate") return "#f2d36b";
  return "#9fc7b3";
}

function el(name, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  svg.appendChild(node);
  return node;
}

el("rect", {x: 0, y: 0, width: W, height: H, fill: "#d9ecf2"});

for (const feature of adm1.features) {
  const parish = feature.properties.shapeName || feature.properties.name || feature.properties.shapeISO;
  const path = el("path", {d: polygonPath(feature.geometry.coordinates), class: "parish"});
  path.dataset.parish = parish;
  path.addEventListener("mouseenter", () => showParish(parish));
  path.addEventListener("click", () => showParish(parish));
  paths.push(path);
}

for (const feature of adm1.features) {
  const parish = feature.properties.shapeName || feature.properties.name || feature.properties.shapeISO;
  const [x, y] = centroid(feature);
  if (parish.length <= 14) {
    const text = el("text", {x, y, class: "label"});
    text.textContent = parish;
  }
}

function activeScenario() {
  return scenarioSelect.value || Object.keys(labels)[0];
}

function applyScenario() {
  const scenario = activeScenario();
  for (const path of paths) {
    const parish = path.dataset.parish;
    const row = scores[scenario][parish];
    path.setAttribute("fill", colorFor(row.category));
    path.setAttribute("opacity", "0.9");
  }
  const ranked = Object.entries(scores[scenario])
    .sort((a, b) => Number(b[1].risk) - Number(a[1].risk))
    .slice(0, 5)
    .map(([parish, row], idx) => `${idx + 1}. ${parish}: ${Number(row.risk).toFixed(1)} (${row.category})`)
    .join("<br>");
  readout.innerHTML = `<strong>${labels[scenario]}</strong><br><br>${ranked}`;
}

function showParish(parish) {
  const scenario = activeScenario();
  const row = scores[scenario][parish];
  readout.innerHTML = `
    <strong>${parish}</strong><br>
    Scenario: ${labels[scenario]}<br>
    Risk index: ${Number(row.risk).toFixed(2)}<br>
    Category: ${row.category}<br>
    Nearest scenario distance: ${Number(row.distance).toFixed(1)} km<br>
    Scenario wind: ${Number(row.wind).toFixed(0)} kt
  `;
}

scenarioSelect.addEventListener("change", applyScenario);
scenarioSelect.value = Object.keys(labels)[0];
applyScenario();
</script>
</body>
</html>
"""
    html = html.replace("__ADM1__", json.dumps(adm1))
    html = html.replace("__SCORES__", json.dumps(scores))
    html = html.replace("__LABELS__", json.dumps(labels))
    SCENARIO_HTML.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()

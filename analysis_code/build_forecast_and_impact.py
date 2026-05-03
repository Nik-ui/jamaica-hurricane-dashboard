import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(r"c:/Users/folah/my_python_projects/jamaica_hurricane_gis")
OUTPUT = BASE / "output"
DATA = BASE / "data"

TRACK_CSV = OUTPUT / "latest_hurricane_full_track.csv"
ADM1_GEOJSON = DATA / "geoBoundaries-JAM-ADM1.geojson"


def parse_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def to_float(v: str):
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def to_int(v: str):
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def fit_slope_intercept(xs, ys):
    n = len(xs)
    if n < 2:
        raise ValueError("Need at least two points")
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, y_mean
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    b1 = sxy / sxx
    b0 = y_mean - b1 * x_mean
    return b1, b0


def polygon_centroid(poly_coords):
    # Approximate centroid using ring vertex mean (sufficient for parish scoring)
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
        lat = sum(c[0] for c in cents) / len(cents)
        lon = sum(c[1] for c in cents) / len(cents)
        return lat, lon
    raise ValueError(f"Unsupported geometry type: {gtype}")


def impact_category(score):
    if score >= 90:
        return "Very High"
    if score >= 65:
        return "High"
    if score >= 40:
        return "Moderate"
    if score >= 20:
        return "Low"
    return "Very Low"


def main():
    with TRACK_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    # Normalize and sort track rows
    track = []
    for r in rows:
        dt = parse_dt(r["iso_time_utc"])
        track.append(
            {
                "storm_sid": r["storm_sid"],
                "storm_name": r["storm_name"],
                "season": int(r["season"]),
                "iso_time_utc": r["iso_time_utc"],
                "epoch_utc": int(r["epoch_utc"]),
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "usa_status": r.get("usa_status") or "",
                "usa_wind_kt": to_int(r.get("usa_wind_kt")),
                "wmo_wind_kt": to_int(r.get("wmo_wind_kt")),
                "nature": r.get("nature") or "",
                "usa_sshs": to_int(r.get("usa_sshs")),
                "dt": dt,
            }
        )

    track.sort(key=lambda x: x["epoch_utc"])
    first = track[0]
    lifecycle_last = track[-1]

    # Focus analysis around Jamaica-impact period for local planning outputs
    jamaica_window = [p for p in track if 16.0 <= p["lat"] <= 20.0 and -80.0 <= p["lon"] <= -74.5]
    base_track = jamaica_window if len(jamaica_window) >= 4 else track
    last = base_track[-1]

    # Forecast model (non-operational): linear trend over last 8 observations (~24h at 3-hour steps)
    window = min(8, len(base_track))
    recent = base_track[-window:]
    xs = [p["epoch_utc"] for p in recent]
    lat_slope, lat_intercept = fit_slope_intercept(xs, [p["lat"] for p in recent])
    lon_slope, lon_intercept = fit_slope_intercept(xs, [p["lon"] for p in recent])

    # Wind trend from latest 8 rows where wind exists
    wind_rows = [p for p in recent if p["usa_wind_kt"] is not None]
    if len(wind_rows) >= 2:
        wx = [p["epoch_utc"] for p in wind_rows]
        wy = [p["usa_wind_kt"] for p in wind_rows]
        wind_slope, wind_intercept = fit_slope_intercept(wx, wy)
        base_wind = last["usa_wind_kt"] or int(round(wind_intercept + wind_slope * last["epoch_utc"]))
    else:
        wind_slope, wind_intercept = 0.0, float(last["usa_wind_kt"] or 0)
        base_wind = int(round(wind_intercept))

    # Build 48-hour forecast at 3-hour intervals
    steps = list(range(3, 49, 3))
    forecast = []
    for h in steps:
        dt = last["dt"] + timedelta(hours=h)
        epoch = int(dt.timestamp())
        plat = lat_intercept + lat_slope * epoch
        plon = lon_intercept + lon_slope * epoch
        pwind = max(20, int(round(wind_intercept + wind_slope * epoch)))
        forecast.append(
            {
                "storm_sid": last["storm_sid"],
                "storm_name": last["storm_name"],
                "season": last["season"],
                "forecast_hour": h,
                "iso_time_utc": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "epoch_utc": epoch,
                "lat": round(plat, 4),
                "lon": round(plon, 4),
                "forecast_wind_kt": pwind,
                "model": "linear_trend_last_24h",
                "confidence_radius_km": 25 + int(h * 2.5),
            }
        )

    forecast_csv = OUTPUT / "forecast_track_48h.csv"
    with forecast_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(forecast[0].keys()))
        writer.writeheader()
        writer.writerows(forecast)

    forecast_geojson = {
        "type": "FeatureCollection",
        "name": "forecast_track_48h",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                "properties": {
                    "storm_sid": r["storm_sid"],
                    "storm_name": r["storm_name"],
                    "season": r["season"],
                    "forecast_h": r["forecast_hour"],
                    "iso_time_utc": r["iso_time_utc"],
                    "f_wind_kt": r["forecast_wind_kt"],
                    "model": r["model"],
                    "conf_km": r["confidence_radius_km"],
                },
            }
            for r in forecast
        ],
    }
    (OUTPUT / "forecast_track_48h.geojson").write_text(json.dumps(forecast_geojson), encoding="utf-8")

    with ADM1_GEOJSON.open("r", encoding="utf-8") as f:
        adm1 = json.load(f)

    # Historical impact proxy: distance-decayed exposure from observed track points near Jamaica
    observed_for_impact = jamaica_window
    if not observed_for_impact:
        observed_for_impact = track

    parish_rows = []
    parish_features = []

    for feat in adm1.get("features", []):
        props = feat.get("properties", {})
        parish_name = props.get("shapeName") or props.get("name") or props.get("shapeISO") or "UNKNOWN"
        c_lat, c_lon = geometry_centroid(feat.get("geometry", {}))

        peak_score = -1.0
        nearest_dist = None
        nearest_time = None
        nearest_wind = None

        for p in observed_for_impact:
            d = haversine_km(c_lat, c_lon, p["lat"], p["lon"])
            wind = p["usa_wind_kt"] if p["usa_wind_kt"] is not None else (p["wmo_wind_kt"] or 35)
            # Exponential distance decay centered on 80 km influence scale
            score = wind * math.exp(-d / 80.0)
            if score > peak_score:
                peak_score = score
                nearest_dist = d
                nearest_time = p["iso_time_utc"]
                nearest_wind = wind

        damage_index = round(min(100.0, peak_score * 1.3), 2)
        cat = impact_category(damage_index)
        row = {
            "parish": parish_name,
            "centroid_lat": round(c_lat, 5),
            "centroid_lon": round(c_lon, 5),
            "impact_index": damage_index,
            "impact_category": cat,
            "nearest_track_time_utc": nearest_time,
            "nearest_track_dist_km": round(nearest_dist, 2) if nearest_dist is not None else None,
            "nearest_wind_kt": nearest_wind,
            "method": "distance_decay_wind_proxy",
        }
        parish_rows.append(row)

        new_props = dict(props)
        new_props.update(row)
        parish_features.append(
            {
                "type": "Feature",
                "geometry": feat.get("geometry"),
                "properties": new_props,
            }
        )

    parish_rows.sort(key=lambda x: x["impact_index"], reverse=True)

    with (OUTPUT / "impact_parish_scores.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(parish_rows[0].keys()))
        writer.writeheader()
        writer.writerows(parish_rows)

    impact_geojson = {"type": "FeatureCollection", "name": "impact_parish_scores", "features": parish_features}
    (OUTPUT / "impact_parish_scores.geojson").write_text(json.dumps(impact_geojson), encoding="utf-8")

    story = {
        "storm_sid": first["storm_sid"],
        "storm_name": first["storm_name"],
        "season": first["season"],
        "started_at_utc": first["iso_time_utc"],
        "started_from": {"lat": first["lat"], "lon": first["lon"]},
        "jamaica_window_start_utc": base_track[0]["iso_time_utc"],
        "jamaica_window_end_utc": base_track[-1]["iso_time_utc"],
        "latest_observed_at_utc": last["iso_time_utc"],
        "latest_observed": {"lat": last["lat"], "lon": last["lon"], "wind_kt": last["usa_wind_kt"]},
        "storm_lifecycle_latest_utc": lifecycle_last["iso_time_utc"],
        "storm_lifecycle_latest": {
            "lat": lifecycle_last["lat"],
            "lon": lifecycle_last["lon"],
            "wind_kt": lifecycle_last["usa_wind_kt"],
        },
        "forecast_horizon_hours": 48,
        "forecast_interval_hours": 3,
        "forecast_model_note": "Simple linear trend from latest 24h within the Jamaica-impact window; planning visualization only.",
        "impact_model_note": "Potential impact proxy from wind and distance; not official loss data.",
    }
    (OUTPUT / "storm_story_summary.json").write_text(json.dumps(story, indent=2), encoding="utf-8")

    print("Wrote:")
    print(OUTPUT / "forecast_track_48h.csv")
    print(OUTPUT / "forecast_track_48h.geojson")
    print(OUTPUT / "impact_parish_scores.csv")
    print(OUTPUT / "impact_parish_scores.geojson")
    print(OUTPUT / "storm_story_summary.json")


if __name__ == "__main__":
    main()

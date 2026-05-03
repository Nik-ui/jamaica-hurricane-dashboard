import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"

IMPACT = OUTPUT / "impact_parish_scores.csv"
VALIDATION = OUTPUT / "forecast_validation_against_observed.csv"
SCENARIOS = OUTPUT / "future_hurricane_scenario_parish_risk.csv"
DASHBOARD = OUTPUT / "arcgis_vs_analysis_dashboard.html"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def top_rows(rows, key, count=8):
    return sorted(rows, key=lambda row: float(row[key]), reverse=True)[:count]


def scenario_summary(rows):
    by_scenario = {}
    for row in rows:
        scenario = row["scenario"]
        by_scenario.setdefault(
            scenario,
            {
                "label": row["scenario_label"],
                "rows": [],
            },
        )
        by_scenario[scenario]["rows"].append(row)

    summary = []
    for scenario, bundle in by_scenario.items():
        ranked = top_rows(bundle["rows"], "future_risk_index", 5)
        summary.append(
            {
                "scenario": scenario,
                "label": bundle["label"],
                "top": [
                    {
                        "parish": row["parish"],
                        "risk": float(row["future_risk_index"]),
                        "category": row["future_risk_category"],
                    }
                    for row in ranked
                ],
            }
        )
    return summary


def main():
    impact_rows = read_csv(IMPACT)
    validation_rows = read_csv(VALIDATION)
    scenario_rows = read_csv(SCENARIOS)

    data = {
        "impact": [
            {
                "parish": row["parish"],
                "impact": float(row["impact_index"]),
                "category": row["impact_category"],
                "distance": float(row["nearest_track_dist_km"]),
                "wind": float(row["nearest_wind_kt"]),
            }
            for row in top_rows(impact_rows, "impact_index", 14)
        ],
        "validation": [
            {
                "hour": int(row["forecast_hour"]),
                "error": float(row["track_error_km"]),
                "wind_error": float(row["wind_error_kt"]),
            }
            for row in validation_rows
        ],
        "scenarios": scenario_summary(scenario_rows),
    }

    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ArcGIS Analysis Workspace</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #eef4f5;
      color: #172026;
    }
    header {
      height: 62px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 0 18px;
      background: #12323d;
      color: #fff;
    }
    h1 {
      font-size: 19px;
      margin: 0;
      font-weight: 700;
    }
    .sub {
      color: #c6dce3;
      font-size: 13px;
    }
    nav {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    button {
      border: 1px solid #7ea1ad;
      background: transparent;
      color: #fff;
      border-radius: 7px;
      padding: 8px 10px;
      cursor: pointer;
      font-size: 13px;
    }
    button.active {
      background: #e8f5f7;
      color: #12323d;
    }
    main {
      height: calc(100vh - 62px);
    }
    section {
      height: 100%;
      display: none;
    }
    section.active {
      display: block;
    }
    iframe {
      width: 100%;
      height: 100%;
      border: 0;
      background: #fff;
    }
    .grid {
      height: 100%;
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
      gap: 14px;
      padding: 14px;
    }
    .panel {
      background: #fff;
      border: 1px solid #cedde2;
      border-radius: 8px;
      overflow: hidden;
      min-height: 0;
    }
    .panel h2 {
      margin: 0;
      padding: 13px 14px;
      font-size: 16px;
      border-bottom: 1px solid #dce7eb;
      background: #f7fbfc;
    }
    .panelBody {
      padding: 14px;
      overflow: auto;
      height: calc(100% - 45px);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      border-bottom: 1px solid #e1eaee;
      padding: 8px 6px;
      text-align: left;
      white-space: nowrap;
    }
    th {
      color: #52646d;
      font-size: 12px;
      background: #f7fbfc;
      position: sticky;
      top: 0;
    }
    .metricGrid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .metric {
      border: 1px solid #dce7eb;
      border-radius: 8px;
      padding: 12px;
      background: #f9fcfd;
    }
    .metric strong {
      display: block;
      font-size: 22px;
      margin-bottom: 4px;
    }
    .metric span {
      color: #60707c;
      font-size: 13px;
    }
    svg {
      width: 100%;
      height: 310px;
      display: block;
    }
    .bar { fill: #1f6f8b; }
    .line {
      fill: none;
      stroke: #ad2f45;
      stroke-width: 3;
    }
    .dot { fill: #ad2f45; }
    .axis {
      stroke: #9babb3;
      stroke-width: 1;
    }
    .tick {
      fill: #52646d;
      font-size: 11px;
    }
    .scenarioCard {
      border: 1px solid #dce7eb;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 10px;
      background: #fbfdfd;
    }
    .scenarioCard h3 {
      margin: 0 0 8px;
      font-size: 14px;
    }
    .scenarioCard ol {
      margin: 0;
      padding-left: 20px;
      font-size: 13px;
      line-height: 1.55;
    }
    @media (max-width: 880px) {
      header {
        height: auto;
        align-items: flex-start;
        flex-direction: column;
        padding: 12px;
      }
      main { height: calc(100vh - 126px); }
      .grid { grid-template-columns: 1fr; }
      .metricGrid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>ArcGIS Analysis Workspace</h1>
      <div class="sub">Hurricane Melissa GIS project: animation, forecast validation, parish exposure, and future scenarios</div>
    </div>
    <nav>
      <button class="active" data-tab="animation">Storm Animation</button>
      <button data-tab="scenarios">Future Scenarios</button>
      <button data-tab="analysis">Analysis Tables</button>
    </nav>
  </header>
  <main>
    <section id="animation" class="active">
      <iframe src="melissa_arcgis_animation.html?v=track-labels-1" title="Hurricane Melissa animation"></iframe>
    </section>
    <section id="scenarios">
      <iframe src="future_hurricane_scenario_explorer.html?v=settlements-storm-motion-1" title="Future hurricane scenario explorer"></iframe>
    </section>
    <section id="analysis">
      <div class="grid">
        <div class="panel">
          <h2>Forecast Validation</h2>
          <div class="panelBody">
            <div class="metricGrid" id="metrics"></div>
            <svg id="errorChart" viewBox="0 0 820 310" role="img" aria-label="Forecast track error by hour"></svg>
            <table id="validationTable"></table>
          </div>
        </div>
        <div class="panel">
          <h2>Parish Exposure and Scenario Summary</h2>
          <div class="panelBody">
            <table id="impactTable"></table>
            <div id="scenarioSummary" style="margin-top:16px"></div>
          </div>
        </div>
      </div>
    </section>
  </main>
<script>
const data = __DATA__;

for (const button of document.querySelectorAll("button[data-tab]")) {
  button.addEventListener("click", () => {
    document.querySelectorAll("button[data-tab]").forEach(b => b.classList.remove("active"));
    document.querySelectorAll("section").forEach(s => s.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.tab).classList.add("active");
  });
}

function renderMetrics() {
  const errors = data.validation.map(d => d.error);
  const mean = errors.reduce((a, b) => a + b, 0) / errors.length;
  const max = Math.max(...errors);
  const final = errors[errors.length - 1];
  const metrics = [
    [`${mean.toFixed(1)} km`, "Mean forecast track error"],
    [`${max.toFixed(1)} km`, "Maximum forecast track error"],
    [`${final.toFixed(1)} km`, "48-hour track error"],
  ];
  document.getElementById("metrics").innerHTML = metrics.map(([value, label]) => `
    <div class="metric"><strong>${value}</strong><span>${label}</span></div>
  `).join("");
}

function renderTable(target, columns, rows) {
  const table = document.getElementById(target);
  table.innerHTML = `
    <thead><tr>${columns.map(c => `<th>${c.label}</th>`).join("")}</tr></thead>
    <tbody>
      ${rows.map(row => `<tr>${columns.map(c => `<td>${c.render ? c.render(row) : row[c.key]}</td>`).join("")}</tr>`).join("")}
    </tbody>
  `;
}

function renderChart() {
  const svg = document.getElementById("errorChart");
  const W = 820, H = 310, pad = 42;
  const maxHour = Math.max(...data.validation.map(d => d.hour));
  const maxErr = Math.max(...data.validation.map(d => d.error)) * 1.08;
  const x = hour => pad + (hour / maxHour) * (W - pad * 1.5);
  const y = err => H - pad - (err / maxErr) * (H - pad * 1.6);
  const path = data.validation.map((d, i) => `${i ? "L" : "M"}${x(d.hour).toFixed(1)},${y(d.error).toFixed(1)}`).join(" ");
  svg.innerHTML = `
    <line class="axis" x1="${pad}" y1="${H - pad}" x2="${W - pad / 2}" y2="${H - pad}"></line>
    <line class="axis" x1="${pad}" y1="${pad / 2}" x2="${pad}" y2="${H - pad}"></line>
    <path class="line" d="${path}"></path>
    ${data.validation.map(d => `<circle class="dot" cx="${x(d.hour)}" cy="${y(d.error)}" r="4"></circle>`).join("")}
    <text class="tick" x="${pad}" y="${H - 10}">0h</text>
    <text class="tick" x="${W - 72}" y="${H - 10}">48h</text>
    <text class="tick" x="8" y="${pad / 2 + 4}">${maxErr.toFixed(0)} km</text>
    <text class="tick" x="8" y="${H - pad + 4}">0 km</text>
  `;
}

function renderScenarios() {
  document.getElementById("scenarioSummary").innerHTML = data.scenarios.map(s => `
    <div class="scenarioCard">
      <h3>${s.label}</h3>
      <ol>${s.top.map(row => `<li>${row.parish}: ${row.risk.toFixed(1)} (${row.category})</li>`).join("")}</ol>
    </div>
  `).join("");
}

renderMetrics();
renderChart();
renderTable("validationTable", [
  {label: "Hour", key: "hour"},
  {label: "Track error km", render: row => row.error.toFixed(2)},
  {label: "Wind error kt", render: row => row.wind_error.toFixed(1)},
], data.validation);
renderTable("impactTable", [
  {label: "Parish", key: "parish"},
  {label: "Impact", render: row => row.impact.toFixed(2)},
  {label: "Category", key: "category"},
  {label: "Distance km", render: row => row.distance.toFixed(1)},
  {label: "Wind kt", render: row => row.wind.toFixed(0)},
], data.impact);
renderScenarios();
</script>
</body>
</html>
"""
    DASHBOARD.write_text(html.replace("__DATA__", json.dumps(data)), encoding="utf-8")
    print(f"Wrote {DASHBOARD}")


if __name__ == "__main__":
    main()

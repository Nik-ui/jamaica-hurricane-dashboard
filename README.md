# Jamaica Hurricane Melissa GIS Dashboard

Interactive GIS dashboard and reproducible Python workflow for analysing parish-scale exposure to Hurricane Melissa (2025) in Jamaica.

Public dashboard:

https://nik-ui.github.io/jamaica-hurricane-dashboard/

## Project Overview

This repository contains the public dashboard and Python analysis scripts for a Hurricane Melissa GIS case study. The project uses open tropical cyclone and administrative boundary data to:

- animate Hurricane Melissa's movement near Jamaica;
- map parish-level wind-distance exposure;
- validate a simple 48-hour GIS forecast against later observed storm positions;
- compare future hurricane corridor scenarios;
- provide reproducible analysis code for academic and disaster-risk communication use.

The project is designed for research visualisation and exposure screening. It is **not** an official meteorological forecast, official warning product, or official damage assessment.

## Live Dashboard

Open the public dashboard here:

https://nik-ui.github.io/jamaica-hurricane-dashboard/

The dashboard includes:

- **Storm Animation**: animated observed storm movement, parish impact layer, forecast path and storm-origin information.
- **Future Scenarios**: interactive comparison of shifted and intensity-adjusted future storm corridor scenarios.
- **Analysis Tables**: parish exposure ranking, forecast validation metrics and scenario summaries.

## Repository Structure

```text
.
├── index.html
├── melissa_arcgis_animation.html
├── future_hurricane_scenario_explorer.html
├── analysis_code/
│   ├── build_forecast_and_impact.py
│   ├── analyze_arcgis_outputs.py
│   ├── build_future_risk_scenarios.py
│   └── build_vs_analysis_dashboard.py
└── README.md
```

## Analysis Code

The reproducible Python scripts are stored in:

```text
analysis_code/
```

### `build_forecast_and_impact.py`

Generates the core GIS outputs:

- 48-hour forecast CSV and GeoJSON;
- parish-level impact score CSV and GeoJSON;
- storm story summary JSON.

The parish impact model uses a distance-decayed wind proxy:

```text
exposure score = wind speed x exp(-distance / 80)
```

This produces a relative exposure index, not a verified damage estimate.

### `analyze_arcgis_outputs.py`

Analyses the ArcGIS-ready project outputs and generates:

- a written GIS analysis report;
- the animated Hurricane Melissa dashboard file;
- forecast validation against later observed track positions.

### `build_future_risk_scenarios.py`

Creates future hurricane corridor scenarios and parish-level future risk outputs. The scenario set includes:

- Melissa-like repeat corridor;
- 50 km west-shifted Category 5 corridor;
- 50 km east-shifted Category 5 corridor;
- Melissa-corridor Category 4 storm;
- 35 km south-shifted Category 5 corridor.

### `build_vs_analysis_dashboard.py`

Builds the tabbed public dashboard from the generated HTML, CSV and JSON outputs.

## Data Sources

The project workflow uses:

- **NOAA IBTrACS** tropical cyclone best-track data;
- **geoBoundaries** Jamaica administrative boundary data;
- derived project CSV and GeoJSON layers.

Key source projects:

- International Best Track Archive for Climate Stewardship (IBTrACS): https://www.ncei.noaa.gov/products/international-best-track-archive
- geoBoundaries: https://www.geoboundaries.org/

## Methods Summary

### 1. Storm Track Processing

Hurricane Melissa's observed track is read from IBTrACS-derived data. Track points are filtered to identify the Jamaica-impact window.

### 2. Parish Exposure Modelling

Each Jamaica parish is represented by an approximate centroid. The model calculates the distance from each parish centroid to each observed storm point and combines distance with wind intensity through an exponential distance-decay function.

### 3. Forecast Generation

A simple 48-hour linear trend forecast is generated from recent storm positions. This is included for GIS visualisation and teaching purposes only.

### 4. Forecast Validation

The simple forecast is validated against later observed track positions. In the project analysis, forecast error increases substantially over 48 hours, showing that the linear model should not be used as an operational forecast.

### 5. Future Scenario Modelling

Future risk is explored through shifted and intensity-adjusted storm corridor scenarios. This supports preparedness-oriented spatial thinking without claiming to predict the exact next hurricane.

## Important Limitations

This project has several limitations:

- The parish exposure index is a wind-distance proxy, not a damage model.
- It does not include rainfall, storm surge, river flooding, slope failure or landslide susceptibility.
- It does not include building-level vulnerability, road disruption, shelter access or hospital capacity.
- It does not use official post-disaster damage assessment data.
- The 48-hour forecast is a simple linear extrapolation and is not operational.
- Future scenarios are exploratory planning scenarios, not probabilistic forecasts.

For operational decisions, use official meteorological and emergency-management sources.

## Academic Use

This repository supports reproducibility for an academic GIS research project. The manuscript itself is **not included in this GitHub repository**. A formatted manuscript package is stored locally by the project author.

Suggested citation wording for the code repository:

```text
Adeniya, F. (2026) Jamaica Hurricane Melissa GIS Dashboard. GitHub repository. Available at: https://github.com/Nik-ui/jamaica-hurricane-dashboard
```

## Public Dashboard URL

```text
https://nik-ui.github.io/jamaica-hurricane-dashboard/
```

## License and Reuse

This repository contains original project code and generated visualisation files. Third-party datasets retain their original licences and citation requirements. Users should cite NOAA IBTrACS and geoBoundaries when reusing the data workflow.

## Status

Current status:

- Dashboard published through GitHub Pages.
- Python analysis code available in `analysis_code/`.
- Manuscript intentionally excluded from the public repository.

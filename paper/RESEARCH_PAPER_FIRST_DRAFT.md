# Parish-Scale GIS Exposure Modelling and Scenario Forecasting for Hurricane Melissa (2025) in Jamaica

## Abstract

Small island states face high tropical-cyclone risk because intense hazards intersect with compact settlement systems, exposed infrastructure and limited spatial redundancy. This paper develops a reproducible geographic information systems (GIS) workflow for assessing parish-scale exposure to Hurricane Melissa (2025) in Jamaica. The analysis integrates tropical cyclone best-track observations from the International Best Track Archive for Climate Stewardship (IBTrACS) with open administrative boundaries from geoBoundaries. Observed storm positions, wind intensity and Jamaica parish geometries are used to create three outputs: an animated storm-track dashboard, a parish-level wind-distance exposure index and a set of future storm-corridor scenarios. The model identifies the highest relative exposure in western and central-western Jamaica, especially Westmoreland, Saint Elizabeth, Hanover, Saint James, Trelawny, Manchester and Saint Ann. Forecast validation shows that the project's simple 48-hour linear track forecast begins with a 35.3 km error but increases to 1155.7 km by 48 hours, demonstrating that simple extrapolation is useful for GIS visualisation but unsuitable for operational forecasting. Future scenario modelling shows that modest eastward or westward shifts in a Category 5 corridor redistribute high-risk parishes substantially. The paper contributes a transparent, open-data workflow for hurricane exposure screening, disaster-risk communication and academic teaching, while identifying the additional datasets required for a full multi-hazard risk model.

**Keywords:** Hurricane Melissa; Jamaica; GIS; tropical cyclones; IBTrACS; disaster risk; parish exposure; scenario forecasting; climate adaptation

## 1. Introduction

Tropical cyclones are among the most destructive hazards affecting the Caribbean. Their impacts are shaped not only by wind intensity and track location, but also by exposure, social vulnerability, infrastructure concentration and land-use patterns. Global tropical cyclone risk has been shown to depend on interactions among hazard, exposed population and vulnerability rather than on storm frequency alone (Peduzzi et al., 2012). For small island states, these interactions are especially important because communities, roads, ports, hospitals, utilities and agricultural zones are often concentrated within short distances of the coast and can be affected simultaneously by wind, rainfall, surge and landslide processes.

Jamaica provides a useful case for parish-scale tropical cyclone exposure analysis. Its administrative parishes offer recognisable planning units, while its settlement pattern combines coastal urban centres, mountainous interior communities and tourism- and agriculture-dependent districts. Hurricane Melissa (2025) provides a recent severe event through which to test how open data and reproducible GIS methods can support spatial risk interpretation. Scientific literature has long connected tropical cyclone destructiveness to storm intensity and lifetime (Emanuel, 2005), while later work emphasises that future losses are likely to be mediated by development, adaptation and exposure as much as by meteorological change (Mendelsohn et al., 2012; Bakkensen and Mendelsohn, 2016). Therefore, an academic GIS analysis should distinguish between hazard exposure, forecast uncertainty and confirmed damage.

This study does not claim to produce an official meteorological forecast or official loss assessment. Instead, it asks how far an open-data GIS workflow can go in translating storm-track observations into parish-level exposure evidence, visual communication layers and future scenario maps. The study uses IBTrACS best-track data because it provides a consolidated global tropical cyclone archive suitable for reproducible research (Knapp et al., 2010). Parish boundaries are drawn from geoBoundaries, an open administrative boundary database designed to support replicable spatial inquiry (Runfola et al., 2020).

## 2. Aim and Research Questions

The aim of this study is to develop and evaluate a reproducible GIS workflow for analysing Hurricane Melissa's spatial exposure pattern in Jamaica and for exploring future hurricane corridor scenarios.

The study addresses four research questions:

1. How did Hurricane Melissa's observed track relate spatially to Jamaica's parishes?
2. Which parishes show the highest relative wind-proximity exposure under the project's distance-decay model?
3. How well does a simple 48-hour linear GIS forecast perform when validated against later observed track positions?
4. How do parish exposure patterns change under plausible future storm-corridor scenarios?

## 3. Literature Context

Risk is commonly conceptualised as a function of hazard, exposure and vulnerability. Tropical cyclone hazards include wind, rainfall, coastal surge and secondary processes such as landslides and infrastructure disruption. Exposure concerns the people, buildings, infrastructure and ecosystems located in hazard-affected areas. Vulnerability concerns the susceptibility of exposed systems to harm. Peduzzi et al. (2012) show that tropical cyclone risk trends cannot be understood from hazard frequency alone because population exposure and vulnerability strongly shape outcomes. This is directly relevant to Jamaica, where a parish may have lower wind exposure but still suffer severe rainfall, road or infrastructure impacts.

There is extensive evidence that tropical cyclone damage potential is sensitive to storm intensity. Emanuel (2005) developed a power-dissipation framing for tropical cyclone destructiveness and linked increases in destructiveness to changes in storm lifetime and intensity. However, there remains uncertainty and debate over how climate change, socioeconomic development and adaptation translate into future losses. Mendelsohn et al. (2012) argue that climate change can increase tropical cyclone damage, but that future economic exposure is also a major driver. Bakkensen and Mendelsohn (2016) further show that adaptation capacity modifies hurricane damages and fatalities. These studies support a scenario-based approach: rather than claiming a single future outcome, a GIS model should compare plausible corridors and intensities.

Best-track data are widely used for tropical cyclone analysis. IBTrACS was designed to unify tropical cyclone data from multiple agencies into a global archive (Knapp et al., 2010). This makes it appropriate for research workflows that require consistent storm position, timing and intensity fields. For administrative boundaries, geoBoundaries provides open, standardised political boundary data that can be integrated into computational GIS workflows (Runfola et al., 2020). Together, these datasets allow a reproducible first-stage exposure model at the parish scale.

## 4. Data and Methods

### 4.1 Study Area

The study area is Jamaica, analysed at parish scale. The fourteen parishes are Kingston, Saint Andrew, Saint Thomas, Portland, Saint Mary, Saint Ann, Trelawny, Saint James, Hanover, Westmoreland, Saint Elizabeth, Manchester, Clarendon and Saint Catherine.

### 4.2 Data Sources

The analysis uses:

- IBTrACS tropical cyclone best-track data for Hurricane Melissa.
- geoBoundaries Jamaica administrative parish boundaries.
- Derived GIS layers generated by the project scripts.

The main generated outputs are:

- `latest_hurricane_full_track.csv`
- `latest_hurricane_near_jamaica.csv`
- `latest_hurricane_points.geojson`
- `latest_hurricane_line.geojson`
- `forecast_track_48h.csv`
- `forecast_track_48h.geojson`
- `impact_parish_scores.csv`
- `impact_parish_scores.geojson`
- `forecast_validation_against_observed.csv`
- `future_hurricane_scenario_parish_risk.csv`
- `future_hurricane_scenario_parish_risk.geojson`
- `arcgis_vs_analysis_dashboard.html`

### 4.3 Observed Jamaica-Impact Window

The full local project track for Melissa contains 93 lifecycle records. The Jamaica-focused window used for analysis contains the observed positions close to Jamaica. In the analysis report, the Jamaica-window track begins on 2025-10-28 00:00 UTC and ends on 2025-10-29 03:00 UTC. The peak wind in the Jamaica-focused window is 165 kt, corresponding to Category 5 intensity under Saffir-Simpson thresholds.

### 4.4 Parish Exposure Index

The parish exposure model uses a distance-decayed wind proxy. First, each parish polygon is assigned an approximate centroid. Second, each observed storm point in the Jamaica-impact window is compared with each parish centroid using the haversine distance. Third, the exposure score is calculated as:

`exposure score = wind speed x exp(-distance / 80)`

The final impact index is scaled and capped at 100. Categories are defined as:

- Very High: 90-100
- High: 65-89.99
- Moderate: 40-64.99
- Low: 20-39.99
- Very Low: below 20

This is a relative exposure index. It is not a damage estimate, fatality estimate or official disaster-loss product.

### 4.5 Forecast Validation

The project generated a 48-hour forecast at 3-hour intervals using a linear trend fitted to recent storm latitude, longitude and wind values. Because later observed IBTrACS positions were available, each forecast point was validated against an interpolated observed position. Track error was calculated using haversine distance.

### 4.6 Future Scenario Modelling

Future hurricane exposure was represented through five exploratory scenarios:

1. Melissa-like repeat corridor.
2. 50 km west-shifted Category 5 corridor.
3. 50 km east-shifted Category 5 corridor.
4. Melissa-corridor Category 4 storm.
5. 35 km south-shifted Category 5 corridor.

Each scenario shifts or rescales the observed Jamaica-impact track, then recalculates parish-level wind-distance exposure. This approach follows the logic that risk planning should test plausible spatial corridors rather than rely on a single deterministic future track.

### 4.7 Reproducibility and Code

The Python code used for the analysis has been added to the GitHub repository:

https://github.com/Nik-ui/jamaica-hurricane-dashboard

The public dashboard is available at:

https://nik-ui.github.io/jamaica-hurricane-dashboard/

The analysis code included in the repository is stored under `analysis_code/` and includes:

- `build_forecast_and_impact.py`
- `analyze_arcgis_outputs.py`
- `build_future_risk_scenarios.py`
- `build_vs_analysis_dashboard.py`

## 5. Results

### 5.1 Observed Track and Intensity

The local full-track dataset begins on 2025-10-21 06:00 UTC and ends on 2025-11-01 06:00 UTC. The maximum recorded wind in the project track is 165 kt near 2025-10-28 12:00 UTC. The Jamaica-window peak is also 165 kt. This confirms that the Jamaica-focused analysis captures the most intense part of the storm lifecycle.

### 5.2 Parish Exposure Ranking

The distance-decayed wind exposure model identifies western and central-western Jamaica as the main exposure zone. Seven parishes are classified as Very High exposure: Trelawny, Saint James, Hanover, Westmoreland, Saint Elizabeth, Manchester and Saint Ann. Clarendon and Saint Mary are classified as High. Saint Catherine, Saint Andrew and Kingston are Moderate, while Portland and Saint Thomas are Low.

| Rank | Parish | Impact index | Category | Nearest track distance (km) | Nearest wind (kt) |
|---:|---|---:|---|---:|---:|
| 1 | Trelawny | 100.00 | Very High | 12.11 | 125 |
| 2 | Saint James | 100.00 | Very High | 32.48 | 145 |
| 3 | Hanover | 100.00 | Very High | 29.78 | 145 |
| 4 | Westmoreland | 100.00 | Very High | 24.16 | 160 |
| 5 | Saint Elizabeth | 100.00 | Very High | 25.79 | 162 |
| 6 | Manchester | 100.00 | Very High | 56.33 | 162 |
| 7 | Saint Ann | 96.35 | Very High | 41.81 | 125 |
| 8 | Clarendon | 72.80 | High | 84.97 | 162 |
| 9 | Saint Mary | 69.48 | High | 54.03 | 105 |
| 10 | Saint Catherine | 57.27 | Moderate | 104.17 | 162 |
| 11 | Saint Andrew | 42.21 | Moderate | 128.59 | 162 |
| 12 | Kingston | 40.65 | Moderate | 131.59 | 162 |
| 13 | Portland | 37.28 | Low | 103.84 | 105 |
| 14 | Saint Thomas | 27.94 | Low | 126.91 | 105 |

### 5.3 Forecast Validation

The simple linear 48-hour forecast had a first-point track error of 35.3 km. Error increased with forecast lead time, reaching 1155.7 km by the final 48-hour point. The mean track error across matched points was 405.1 km. This result is methodologically important: a linear GIS extrapolation can help visualise short-range motion, but error grows rapidly and the method cannot replace official dynamical or ensemble forecast products.

### 5.4 Future Scenario Results

The future scenario model shows that parish risk is corridor-sensitive. A Melissa-like repeat corridor continues to emphasise western and central-western Jamaica. A west-shifted Category 5 corridor further concentrates exposure in western parishes. An east-shifted Category 5 corridor increases relative exposure in Manchester, Clarendon, Saint Catherine, Kingston, Saint Andrew and Saint Mary. This supports the use of scenario modelling in preparedness planning, especially for small islands where small track shifts can produce substantially different spatial exposure patterns.

## 6. Discussion

The results show that the highest modelled exposure occurs where the most intense segment of Melissa's track passes closest to parish centroids. This is consistent with the physical expectation that wind hazard decreases with distance from the storm centre, while also showing the value of spatially explicit analysis. A table of storm positions alone cannot show which administrative units are most exposed; a GIS layer can.

The forecast validation is equally important. It prevents overclaiming. The project forecast layer is useful for animation, teaching and demonstrating how GIS forecast products can be built, but validation shows that a simple linear model becomes unreliable over 24-48 hours. This aligns with the broader need for uncertainty-aware tropical cyclone communication. Peer-reviewed risk literature also supports a cautious interpretation of forecast products: disaster impacts depend on exposure and vulnerability as well as hazard intensity (Peduzzi et al., 2012; Bakkensen and Mendelsohn, 2016).

The scenario model improves the paper's future-looking contribution. It does not pretend to predict the next hurricane. Instead, it tests how parish exposure changes if a future storm follows a similar, shifted or weaker corridor. This framing is more defensible for academic publication because it treats future hurricane risk as a planning problem under uncertainty. It also connects to evidence that future tropical cyclone losses are shaped by both climate-related hazard changes and socioeconomic exposure (Mendelsohn et al., 2012).

## 7. Limitations

The model has several limitations.

First, parish centroids simplify the spatial complexity of each parish. Exposure within a parish is not uniform. Second, the wind-distance model does not include rainfall, storm surge, river flooding, slope failure, building vulnerability, shelter access or road disruption. Third, the model does not use official post-event damage data, so it should be described as exposure modelling rather than damage modelling. Fourth, the forecast is a simple linear extrapolation, not an operational meteorological model. Fifth, the future scenarios are exploratory corridor tests and should not be interpreted as probabilistic forecasts.

## 8. Conclusion

This paper develops a reproducible GIS workflow for parish-level hurricane exposure analysis in Jamaica. Using Hurricane Melissa (2025) as a case study, the model identifies western and central-western parishes as the highest relative exposure zone. The animated dashboard communicates storm movement, parish impact categories and forecast uncertainty. Forecast validation shows that simple linear extrapolation is not suitable for operational prediction beyond short lead times. Future scenario modelling demonstrates that modest spatial shifts in a Category 5 corridor can substantially redistribute parish exposure.

The contribution of the study is methodological and communicative. It shows how open tropical cyclone and administrative boundary datasets can be transformed into reproducible GIS outputs for academic analysis, disaster-risk communication and preparedness planning. Future work should integrate population, buildings, road networks, shelters, hospitals, elevation, rainfall, storm surge and verified damage data to produce a more complete multi-hazard risk model for Jamaica.

## References

Bakkensen, L.A. and Mendelsohn, R.O. (2016) 'Risk and adaptation: evidence from global hurricane damages and fatalities', *Journal of the Association of Environmental and Resource Economists*, 3(3), pp. 555-587. doi: 10.1086/685908.

Emanuel, K. (2005) 'Increasing destructiveness of tropical cyclones over the past 30 years', *Nature*, 436(7051), pp. 686-688. doi: 10.1038/nature03906.

Knapp, K.R., Kruk, M.C., Levinson, D.H., Diamond, H.J. and Neumann, C.J. (2010) 'The International Best Track Archive for Climate Stewardship (IBTrACS): unifying tropical cyclone data', *Bulletin of the American Meteorological Society*, 91(3), pp. 363-376. doi: 10.1175/2009BAMS2755.1.

Mendelsohn, R., Emanuel, K., Chonabayashi, S. and Bakkensen, L. (2012) 'The impact of climate change on global tropical cyclone damage', *Nature Climate Change*, 2, pp. 205-209. doi: 10.1038/nclimate1357.

Peduzzi, P., Chatenoux, B., Dao, H., De Bono, A., Herold, C., Kossin, J., Mouton, F. and Nordbeck, O. (2012) 'Global trends in tropical cyclone risk', *Nature Climate Change*, 2, pp. 289-294. doi: 10.1038/nclimate1410.

Runfola, D., Anderson, A., Baier, H., Crittenden, M., Dowker, E., Fuhrig, S., Goodman, S., Grimsley, G., Layko, R., Melville, G. et al. (2020) 'geoBoundaries: a global database of political administrative boundaries', *PLOS ONE*, 15(4), e0231866. doi: 10.1371/journal.pone.0231866.

## Appendix A: Suggested Figures

Figure 1. Jamaica parish boundary and Hurricane Melissa observed track.

Figure 2. Parish-level wind-distance exposure index.

Figure 3. Animated storm-position dashboard still.

Figure 4. Forecast validation chart showing track error by forecast hour.

Figure 5. Future scenario comparison map for shifted Category 5 corridors.

## Appendix B: Code Availability

Python analysis scripts are available in the GitHub repository:

https://github.com/Nik-ui/jamaica-hurricane-dashboard/tree/main/analysis_code

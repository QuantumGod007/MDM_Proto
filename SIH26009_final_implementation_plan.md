# SIH26009 — Final Demo Implementation Plan

**Goal:** Build a credible 60–70% college-demo prototype for the problem statement “Using AI/ML and Space Technology to Identify Manganese Reserves and Overcome Production Shortfalls.”

The demo will reuse the team’s existing map application, show public geological and satellite context, forecast production using clearly labelled simulated operations data, and let the user try simple corrective-action scenarios. It demonstrates a workflow; it is not a validated MOIL reserve or production system.

## 1. What the problem asks for

The problem statement asks for a system that combines geological data, production and equipment information, and satellite/weather inputs to:

1. Identify and map manganese reserves using surface and subsurface indicators.
2. Predict possible production shortfalls and their contributing constraints.
3. Suggest corrective actions and present useful information in a dashboard.

For this demo, public occurrence locations and satellite imagery provide spatial context. Detailed MOIL drill, assay, production, equipment, and blasting records are not available in the required detail, so the production forecast uses simulated operations data. Do not claim simulated outputs are real MOIL predictions.

## 2. Demo workflow

The complete presentation flow should be:

**Open the existing map → select one demo mine area → view known manganese locations and satellite context → view a production target and forecast → inspect risk factors → change an operational scenario → compare the result.**

Use one demo area consistently throughout the map, weather data, forecast panel, and presentation. If using Dongri Buzurg, verify its location and label it as the selected study area.

## 3. Dataset plan

Use these five dataset groups. Keep source, retrieval date, units, spatial/temporal resolution, and real/simulated status in a `data_sources.md` file.

| Dataset | Use in the demo | Preparation and limitations |
|---|---|---|
| **GSI manganese deposit locations** | Real map points and geological context | Download the spreadsheet/ZIP from the [OGD catalog](https://tn.data.gov.in/catalog/location-manganese-ore-deposits-india-and-its-salient-features). Clean names and coordinates, remove duplicates, and convert to the map’s accepted format (prefer GeoJSON for points). The catalog was last updated in 2014; it is not a drill-hole, assay, grade, or pixel-level reserve-label dataset. |
| **IBM Indian Minerals Yearbook 2024** | Official reported mine-level reserve/resource figures where available | Extract only figures that can be matched reliably to a mine. Preserve the unit, classification, reporting date, and PDF page in a CSV. Show figures in a popup/card or mine summary; do not spread one mine total across map pixels. [Yearbook PDF](https://www.ibm.gov.in/writereaddata/files/177426215469c1178a48453IMYB_2024_EBookFinal.pdf) |
| **Sentinel-2 imagery/context** | Satellite basemap or one surface-context layer | Reuse the existing map’s imagery support if available. Otherwise, use one clear cloud-free image/date for the selected area. Imagery provides surface context; it does not directly reveal underground manganese reserves. [Earth Engine catalog](https://developers.google.com/earth-engine/datasets/catalog/sentinel-2) |
| **Regional gridded rainfall** | Real weather context for the production scenario | Prefer India’s daily rainfall grid at 0.25° resolution (roughly 25 km) from [IMD Climate Research Services](https://imdpune.gov.in/lrfindex.php/cmpg/Models_Forecast/latestnews/cmpg/Griddata/rti.php). NASA POWER is an allowed fallback. The current Person 2 file uses NASA POWER daily rainfall at 0.5° (roughly 50 km), aggregated weekly; label it regional, not an on-site gauge measurement. |
| **Simulated weekly operations** | Train and demonstrate production forecasting | Generate weekly rows for the selected demo area with planned tonnes, actual tonnes, equipment downtime/availability, blasting delay, and rainfall. Mark every row/file/chart `SIMULATED`. These are not MOIL records. |

### Clean and standardize the files

- Keep raw downloads unchanged in `data/raw/`; put cleaned files in `data/processed/`.
- Standardize coordinate order and use WGS84 latitude/longitude for map points.
- Check that coordinates are numeric, non-empty, within India, and consistent with the chosen area. Keep an audit of any removed duplicate or invalid row.
- Normalize mine/state names, but retain the original name in a separate column.
- Store reserve/resource amounts as numeric tonnes and retain the published classification and as-of date.
- Parse rainfall dates into ISO format (`YYYY-MM-DD`), use millimetres consistently, and record missing values rather than silently replacing them.
- Aggregate daily rainfall to weekly totals to align it with weekly operations data.
- Every cleaned record or layer should retain a source URL and a `data_status` such as `public_reference`, `official_reported`, or `simulated`.

Suggested files:

```text
data/
  raw/
  processed/
    gsi_manganese.geojson
    ibm_mine_figures.csv
    rainfall_daily.csv
    rainfall_weekly.csv
    simulated_operations_weekly.csv
    forecast_results.csv
data_sources.md
```

## 4. Map and spatial presentation

1. Run the existing map repository unchanged and record how to launch it, its framework, and the data formats it accepts.
2. Add the cleaned GSI occurrence points as the first new layer. Verify several markers against their coordinates and make each popup show the occurrence name, location, source, source year, and status.
3. Add available IBM mine-level figures only when the mine-to-location match is reliable. Label them “official reported reserve/resource figure” and display the reporting date and classification.
4. Add one Sentinel-2 view or supported surface-context layer. Include the imagery date and source.
5. Keep the layers visually distinct: **Known GSI occurrences**, **IBM-reported mine figures**, and **Satellite context**. Do not label an ML-generated or synthetic map surface as a confirmed reserve map.

**No manganese-reserve classifier is required for this demo.** The GSI locations do not provide verified positive and negative labels for every map cell. A trained model that colours pixels as confirmed ore would be misleading without drill/assay ground truth. If the existing map already has a score layer, relabel it as experimental screening/context or turn it off for this presentation.

## 5. Production shortfall model

### Dataset and prediction target

Use one row per week for the selected demo area. Generate enough synthetic history to illustrate training and a time holdout (for example, 3–5 years of weekly rows). Document the rules used to generate each simulated field.

Suggested columns:

| Column | Meaning |
|---|---|
| `week_start` | Start date of the operating week |
| `planned_tonnes` | Planned output for that week |
| `actual_tonnes` | Simulated output; target used for training |
| `rainfall_mm` | Weekly total from the selected-area IMD rainfall series |
| `downtime_hours` | Simulated equipment downtime |
| `equipment_available_pct` | Simulated equipment availability |
| `blast_delay_hours` | Simulated delay |
| `actual_tonnes_lag_1` | Previous week’s production, available before the forecast week |
| `rolling_mean_4` | Mean production over the previous four weeks only |
| `data_status` | `simulated` for operations rows |

Do not include information that would only be known after the prediction week. Avoid using the current week’s `actual_tonnes` to predict that same week. For a one-week-ahead forecast, use rainfall observed before the target week (or a weather forecast available at prediction time), along with planned operating inputs; do not use the target week’s realized rainfall as if it were known in advance.

### Models and evaluation

1. **Baseline:** predict using a trailing average (for example, the previous four weeks).
2. **Main demo model:** train a `RandomForestRegressor` to predict next-week `actual_tonnes`. Random Forest is the primary choice because it is practical for tabular data and straightforward to explain. XGBoost may be tried as an optional comparison if time allows; keep the model with lower error on the same holdout, not the model with the more impressive name.
3. Split chronologically: train on earlier weeks and evaluate on later weeks. Do not randomly shuffle the time series.
4. Report MAE in tonnes for both models and show predicted versus simulated actual output for the holdout weeks.
5. If Random Forest does not beat the baseline, show both and explain that the demo data/model needs improvement. Do not manufacture a good score.

The dashboard can calculate:

```text
forecast_gap_tonnes = planned_tonnes - forecast_tonnes
shortfall_pct = max(0, forecast_gap_tonnes / planned_tonnes * 100)
```

Use clearly described demo risk thresholds (for example, below 5% = low, 5–10% = medium, above 10% = high). These are prototype thresholds, not MOIL policy.

## 6. Recommendations and “what-if?” scenarios

Use transparent rule-based actions rather than another trained model:

- If simulated downtime is high, suggest checking maintenance status or reallocating available equipment.
- If blast delay is high, suggest reviewing the blast schedule.
- If forecast output falls below plan, show the shortfall and rank the applicable actions.

Provide at least two controls: reduce downtime/increase availability, and reduce blasting delay. Recalculate the scenario forecast and show the baseline beside it. State that scenario improvements depend on the synthetic assumptions; they are not proven causal effects.

## 7. Dashboard requirements

The demo screen should include:

- Existing interactive map with the selected area and layer controls.
- Summary of known occurrences and any matched IBM-reported mine figure.
- Satellite context with date/source.
- Simulated actual versus plan production chart.
- Baseline forecast and Random Forest forecast, with MAE from the chronological holdout.
- Forecast tonnes, target tonnes, gap, gap percentage, and risk band.
- Main model inputs/risk contributors, described as model associations rather than proven causes.
- Two working “what-if?” controls and a before/after scenario comparison.
- Persistent status labels for public, officially reported, experimental, and simulated data.

## 8. Build sequence and milestones

### Milestone 1 — Map starts cleanly

- Run the existing project from a fresh start.
- Confirm the map framework, expected layer format, and how to configure the demo area.
- Choose and record the one study area.

**Done when:** another teammate can launch the map using the written steps.

### Milestone 2 — First real dataset on the map

- Download and clean the GSI file.
- Convert to the map’s accepted point format.
- Add markers, popups, source, and status labels.

**Done when:** GSI points appear in plausible locations and popups identify them as documented occurrences.

### Milestone 3 — Add official and satellite context

- Extract any reliable IBM figure for the chosen mine and record its source details.
- Add the Sentinel-2 context layer.
- Add IMD rainfall and convert it to a weekly series for the forecast periods.

**Done when:** each layer has provenance, dates, units, and an honest description of its limitations.

### Milestone 4 — Build and evaluate the forecast

- Generate the simulated operations CSV and document its assumptions.
- Implement the trailing-average baseline and Random Forest model.
- Evaluate on a chronological holdout and save forecast results.

**Done when:** model output, baseline output, and MAE are reproducible from the saved data and code.

### Milestone 5 — Integrate scenario controls and rehearse

- Connect the selected demo area to its chart and forecast panel.
- Add two what-if controls and rule-based recommendations.
- Test labels, units, source notes, and the full demo path.

**Done when:** the team can deliver the demo without editing code or hiding data limitations.

## 9. Four-person work division

Each person should work against the same selected demo area and use the file names and fields below. Person 4 can begin the dashboard with sample/mock outputs while the other data files and model are being prepared.

### Person 1 — Geological reference data

1. Download the GSI manganese-deposit spreadsheet/ZIP from the linked OGD catalog.
2. Inspect the columns and identify locality, state, coordinates, host rock, and geological description where available.
3. Clean blank/invalid coordinates, normalize state/locality names, remove exact duplicates, and keep a copy of the raw file unchanged.
4. Check records for the selected demo region. Convert usable points into `data/processed/gsi_manganese.geojson` using WGS84 coordinates.
5. Extract a matching IBM Yearbook figure only if the mine/location match is reliable. Save it to `data/processed/ibm_mine_figures.csv` with `mine_name`, `district`, `amount_tonnes`, `classification`, `as_of_date`, `source_page`, and `match_note`.
6. Provide a short provenance note: dataset date, source URL, fields retained, and known limitations.

**Handoff:** GeoJSON and IBM CSV, with source details. Occurrence points must be labelled as documented occurrences; reported figures must retain their reporting date/classification.

### Person 2 — Satellite and rainfall inputs

1. Prepare one Sentinel-2 surface-context view for the selected area, using the project’s existing imagery workflow where possible. Record image date, cloud/context limitations, source, and layer format.
2. Obtain daily IMD gridded rainfall for the selected area. Use the official IMD archive or the CSV export path linked in the dataset section.
3. Clean dates, units, and missing values; keep rainfall in millimetres. Save daily values to `data/processed/rainfall_daily.csv` and aggregate them into weekly totals in `data/processed/rainfall_weekly.csv`.
4. Record the rainfall grid resolution and state clearly that it is regional rainfall, not an on-site gauge reading.
5. Hand off the imagery layer/configuration and rainfall CSV with metadata in `data_sources.md`.

**Handoff:** One satellite/context layer and a weekly rainfall series keyed by week/date for the selected demo area.

### Person 3 — Simulated operations data and ML

1. Create `data/processed/simulated_operations_weekly.csv` with one row per week and the columns defined in Section 5. Join the real weekly rainfall series by date; generate only the unavailable operations fields (production, equipment, and blasting) synthetically.
2. Document the rules and random seed used to generate synthetic values. Include `data_status=simulated` and do not describe the rows as MOIL records.
3. Train a `RandomForestRegressor` to predict next-week simulated production. Create the trailing-four-week moving-average baseline.
4. Use a chronological split: earlier weeks for training, later weeks for holdout. Report MAE for both predictions and save the holdout comparison to `data/processed/forecast_results.csv`.
5. Write one callable prediction function or small API that accepts the scenario inputs and returns forecast tonnes, baseline tonnes, MAE, and risk inputs.
6. Confirm there is no leakage from the future week’s actual production into the model features.

**Handoff:** Simulated data CSV, model/training code, evaluation summary, prediction interface, and a sample base/scenario forecast. All results must remain labelled simulated.

### Person 4 — Dashboard integration and presentation

1. Build the page flow and dashboard panels using temporary sample data while waiting for the other handoffs.
2. Connect Person 1’s GeoJSON and available IBM figures, Person 2’s satellite/rainfall outputs, and Person 3’s forecast interface/results.
3. Display distinct map layers and source/status popups; show the satellite date and rainfall resolution.
4. Add production target, simulated history, baseline forecast, Random Forest forecast, gap, risk band, and the holdout MAE.
5. Add two working scenario controls: reduce downtime/increase availability and reduce blast delay. Show base and scenario forecasts together.
6. Add transparent rule-based recommendations and persistent public/official/simulated status labels.
7. Prepare slides and a short run-of-show covering the problem, data sources, demo flow, forecast method, scenario, and limitations.

**Handoff:** Integrated demo build, source/status labels visible in the app, presentation slides, and a concise click-by-click demo script.

### Shared handoff rules

- Agree the demo-area name and `week_start` format before creating files.
- Person 4 shares the expected frontend data shape on Day 1; everyone uses those field names or agrees changes before integration.
- Keep raw files immutable; put cleaned outputs in `data/processed/`.
- Every file must include or be accompanied by source, date, units, resolution, and real/simulated status.
- Integrate as soon as each deliverable is ready; do not wait until all datasets and the model are finished.
- All four review the final data labels and rehearse the same end-to-end story.

## 10. Three-minute demo narrative

1. **Problem:** production planning can be affected by spatial uncertainty and operational shortfalls.
2. **Map:** select the demo area and show GSI occurrences, the reported mine figure if available, and satellite context.
3. **Data transparency:** explain that map/weather layers are public sources, while mine-level operations rows are simulated because detailed MOIL logs are not publicly available.
4. **Forecast:** compare simulated actual-versus-plan, the moving-average baseline, and Random Forest forecast; show the time-holdout MAE.
5. **Action:** adjust downtime or blast delay and compare the scenario forecast.
6. **Limitations and next step:** explain that real drill/assay and operations data are needed to validate reserve screening and production predictions for MOIL.

## 11. Ready-to-present checklist

- [ ] Existing map launches reliably from written steps.
- [ ] GSI points show the correct coordinates and source details.
- [ ] IBM values, if shown, include classification, units, as-of date, and mine match confidence.
- [ ] Sentinel-2 and IMD layers state their date/resolution and are described as context.
- [ ] Every generated operations file, chart, and result is labelled simulated.
- [ ] Random Forest and baseline are evaluated with a chronological holdout and MAE.
- [ ] Forecast panel shows target, predicted output, shortfall gap, and risk band.
- [ ] Two scenario controls visibly change the demo output.
- [ ] Slides separate documented occurrences, reported mine figures, model outputs, and assumptions.
- [ ] No one claims satellite imagery alone verifies underground ore, or simulated production results represent actual MOIL output.

## 12. What remains beyond this demo

The next stage would require approved MOIL drill-hole and assay data, surveyed geology/geophysics, mine-level historical production targets and actuals, equipment and maintenance telemetry, blasting/shift logs, and expert validation. With those inputs, the team could assess whether a spatial prospectivity model or operational shortfall model is supportable and evaluate it against independent holdout sites/time periods.

## Sources

- [GSI manganese deposit locations — Open Government Data Platform India](https://tn.data.gov.in/catalog/location-manganese-ore-deposits-india-and-its-salient-features)
- [Indian Bureau of Mines — Indian Minerals Yearbook 2024](https://www.ibm.gov.in/writereaddata/files/177426215469c1178a48453IMYB_2024_EBookFinal.pdf)
- [Sentinel-2 catalog — Google Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/sentinel-2)
- [IMD Climate Research Services — gridded data archive](https://imdpune.gov.in/lrfindex.php/cmpg/Models_Forecast/latestnews/cmpg/Griddata/rti.php)
- [IMDWeb rainfall data selection and CSV export](https://imdweb.lwcc.in/)
- [NASA POWER API tutorial — fallback data resolution](https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/)

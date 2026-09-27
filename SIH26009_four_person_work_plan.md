# SIH26009 Demo — Four-Person Work Plan

## Demo goal

Show one complete workflow: select a manganese mine area, view its public map context, see a production forecast, and test an operational scenario. The demo uses public spatial/weather data and clearly labelled simulated operations data.

## Person 1 — GSI and IBM geological data

### Tasks

1. Download the GSI manganese locations spreadsheet/ZIP from the [OGD dataset page](https://tn.data.gov.in/catalog/location-manganese-ore-deposits-india-and-its-salient-features).
2. Keep a copy of the raw download. Clean usable rows:
   - Standardize locality and state names.
   - Check latitude and longitude are numeric and fall in India.
   - Remove exact duplicate or invalid-coordinate rows.
   - Keep geological description and host-rock columns where available.
3. Convert the cleaned points to GeoJSON using WGS84 coordinates.
4. Check the [IBM Indian Minerals Yearbook 2024](https://www.ibm.gov.in/writereaddata/files/177426215469c1178a48453IMYB_2024_EBookFinal.pdf) for a reserve/resource figure for the selected mine. Include it only if the mine match is reliable.
5. For each figure, retain its amount, unit, classification, as-of date, PDF page, and source.

### Deliverables

- `gsi_manganese.geojson`
- `ibm_mine_figures.csv`, if a reliable figure is available
- A short note listing source, date, fields, and limitations

### Done when

GSI points appear in the correct locations, and each point is identified as a documented occurrence—not a newly verified reserve.

## Person 2 — Sentinel-2 and rainfall data

### Tasks

1. Prepare a Sentinel-2 image or surface-context layer for the selected area. Record the image date, source, and any cloud limitations.
2. Prefer daily rainfall from IMD for the selected area using the [IMD data archive](https://imdpune.gov.in/lrfindex.php/cmpg/Models_Forecast/latestnews/cmpg/Griddata/rti.php). NASA POWER is an allowed fallback; the current 2021–2024 rainfall files use NASA POWER at 0.5° resolution, not IMD. The [IMDWeb tool](https://imdweb.lwcc.in/) may help export an IMD selected-area CSV if the team later switches sources.
3. Clean dates, missing values, and units. Keep rainfall in millimetres.
4. Aggregate daily rainfall into weekly totals to match the production data.
5. Record the grid resolution and label it as regional rainfall, not an on-site gauge measurement.

### Deliverables

- Sentinel-2 layer or image plus its source/date note
- `rainfall_daily.csv`
- `rainfall_weekly.csv`
- Source and resolution details for the app

### Done when

The image/context layer and rainfall series are ready for the selected area and have clear provenance.

## Person 3 — Simulated operations data and ML training

### Tasks

1. Create one weekly row per period in `simulated_operations_weekly.csv`.
2. Use the real weekly rainfall series from Person 2. Generate only the unavailable operations fields synthetically, such as planned output, actual output, equipment downtime, and blasting delay.
3. Include `data_status=simulated`. Document the generation rules and random seed.
4. Train a `RandomForestRegressor` to predict next-week production using information available before that week, such as:
   - Planned tonnes
   - Rainfall known before the forecast week (a lagged observation or a weather forecast)
   - Downtime or equipment availability
   - Blasting delay
   - Previous production and rolling average
5. Compare it with a trailing-four-week moving-average baseline.
6. Use earlier weeks for training and later weeks for the holdout. Report MAE for both models. Do not randomly shuffle the weeks.
7. Prevent data leakage: the target week’s actual production must not be used as an input for predicting that same week.
8. If time allows, compare XGBoost using the same holdout and keep the model with lower MAE.

### Deliverables

- `simulated_operations_weekly.csv`
- Model/training code
- `forecast_results.csv`
- MAE comparison and one example forecast
- A prediction function or API that the dashboard can call

### Done when

The forecast and baseline are reproducible from the saved data and code, with simulated status clearly visible.

## Person 4 — Dashboard, scenarios, and presentation

### Tasks

1. Build the demo page flow and panels using sample values while the data/model work is underway.
2. Connect the GSI points and any reliable IBM figure from Person 1.
3. Connect Person 2’s satellite and rainfall outputs.
4. Connect Person 3’s forecast output and prediction function.
5. Display:
   - Map layers and source/status popups
   - Production target and simulated history
   - Baseline and Random Forest forecasts
   - Forecast gap, gap percentage, risk band, and holdout MAE
6. Add two “what-if?” controls:
   - Reduce downtime or increase equipment availability
   - Reduce blasting delay
7. Show the base and scenario forecasts together. Add rule-based recommendations with a short reason.
8. Keep visible labels for **public data**, **official reported figures**, and **simulated operations data**.
9. Prepare slides and a short demo script that explains the data limitations honestly.

### Deliverables

- Integrated dashboard
- Working scenario controls and recommendations
- Presentation slides and click-by-click demo script

### Done when

Selecting the demo area, viewing the forecast, and changing a scenario all work in one presentation flow.

## Shared working rules

- Agree on one demo area and weekly date format before preparing data.
- Use the filenames in this plan; agree on any column-name changes before integration.
- Keep raw downloads unchanged; save cleaned files in `data/processed/`.
- Record source, retrieval date, units, resolution, and real/simulated status for every dataset.
- Integrate each completed item as it becomes available; use sample data in the dashboard until real files arrive.
- Everyone rehearses the same demo story and avoids describing simulated output as actual MOIL production.

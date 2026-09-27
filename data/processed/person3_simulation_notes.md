# Person 3 simulated operations data

`simulated_operations_weekly.csv` joins one synthetic operations row to each of Person 2's weekly rainfall rows. The selected study area is Dongri Buzurg, but operations use the fictional ID `DEMO-01` so they cannot be mistaken for MOIL records. Run `python3 scripts/generate_simulated_operations.py` to reproduce the table; the random seed is `26009`.

## What is real and what is simulated

- `rainfall_mm` is copied from Person 2's NASA POWER daily series, aggregated into complete Monday-starting weeks. It is public regional gridded rainfall at 0.5° (about 50 km), not a mine rain-gauge reading. The daily input covers 2021-01-01 to 2024-12-31; the processed weekly file has 208 weeks from 2021-01-04 to 2024-12-23. NASA POWER is the source used here; this is not IMD data. Retrieval date recorded by Person 2: 2026-09-27. Units are millimetres per week. Source docs: <https://power.larc.nasa.gov/docs/services/api/temporal/daily/>.
- `planned_tonnes`, `actual_tonnes`, `downtime_hours`, `equipment_available_pct`, and `blast_delay_hours` are synthetic demo values. They are not MOIL operating records.
- `rainfall_mm_previous_week`, `actual_tonnes_lag_1`, and `rolling_mean_4` use only earlier weeks. The current week's measured rainfall is retained for context and should not be used as an input to a one-week-ahead prediction.
- The operations rows use `data_status=simulated` (also repeated as `operations_data_status=simulated`); the rainfall retains Person 2's own source and status fields.
- `demo_site_id=DEMO-01` is a fictional dashboard key for the Dongri Buzurg study-area demonstration. `rainfall_source_site_id` preserves the ID in the rainfall source; it does not make the synthetic operations data real.

## Generation assumptions

- The illustrative plan level is about 1,000 tonnes per week, with a small seasonal variation and random noise. This scale is an arbitrary demo assumption, not a reported Dongri Buzurg target.
- Weekly downtime and blast delay are generated within illustrative bounds of 0–30 hours and 0–10 hours.
- Synthetic output is reduced by assumed downtime, blast delay, and previous-week rainfall effects, with a carryover term and random noise. The coefficients are invented to make a controllable demonstration; they are not measured causal effects.
- Output is capped at the synthetic plan and floored at zero.

Model scores calculated from these targets must be described as performance on a simulated holdout. They are not evidence of accuracy on real MOIL production.

## Forecast handoff

- Run `python3 scripts/train_production_model.py` to create `forecast_results.csv`, `forecast_metrics.json`, and `models/random_forest_model.joblib`.
- The evaluation uses the first 80% of usable weeks for training and the final 20% as a chronological rolling one-week-ahead holdout. The model is held fixed during that period, while each prior simulated actual is used for the next week's lag features; weeks are not shuffled.
- The holdout forecasts and MAEs are calculated before refitting the saved serving model. The saved `random_forest_model.joblib` is then fit on all 204 usable synthetic rows (2021-02-01 through 2024-12-23); this does not change the evaluation results.
- The baseline is the mean of the previous four simulated actual outputs. The Random Forest uses the planned target, previous-week rainfall, simulated pre-week downtime and blast-delay estimates, availability, and previous production history.
- The prediction function returns both forecasts, gaps, risk bands, the inputs behind the prediction, holdout MAEs, and warnings for values outside the synthetic training ranges. Downtime and blast delay are scenario estimates, not future observed logs.
- `src/forecast_model.py` exports `predict_next_week(...)` for Person 4. Pass the next week's plan and pre-week assumptions plus the latest lag/rolling production values. The function returns both forecasts, their gaps, demo risk bands, input values, holdout metrics, and any training-range warnings.
- Demo risk bands are illustrative: below 5% shortfall is low, 5–10% is medium, and above 10% is high. These are not MOIL policy.

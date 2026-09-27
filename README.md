# MDM_Proto — SIH26009 manganese planning prototype

This repository contains the production-forecasting component for the SIH26009 demo. The prototype demonstrates a one-week-ahead shortfall-planning workflow for the Dongri Buzurg study area. It is not a validated MOIL production model or a reserve-estimation system.

## Data boundary

- `data/processed/rainfall_weekly.csv` is public regional NASA POWER rainfall at 0.5° resolution, aggregated weekly by Person 2. It is not an on-site gauge series.
- `data/processed/simulated_operations_weekly.csv` combines that timeline with synthetic planned/actual tonnes, downtime, availability, and blast delay. `DEMO-01` is a fictional dashboard key for the Dongri Buzurg study-area demo. Every operations row is marked `data_status=simulated`.
- The synthetic weekly plan is centered around 1,000 tonnes only as an illustrative scale. It is not a reported mine target.
- Model scores measure fit to the simulated assumptions only. They must not be presented as MOIL accuracy.

## Run the Person 3 pipeline

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-person3.txt
python3 scripts/generate_simulated_operations.py
python3 scripts/train_production_model.py
```

The checked-in `joblib` model was created with Python 3.13.2 and the exact package versions in `requirements-person3.txt`. Use that environment when loading the artifact; scikit-learn does not guarantee cross-version model compatibility.

The training script creates:

- `data/processed/forecast_results.csv` — chronological holdout predictions against simulated actuals;
- `data/processed/forecast_metrics.json` — split dates, holdout MAE for both models, feature ranges, seed, package versions, and descriptive feature importances;
- `data/processed/forecast_example.json` — reproducible base and what-if scenario inputs and outputs;
- `models/random_forest_model.joblib` — fitted Random Forest for the dashboard prediction function.

The split is chronological and unshuffled: earlier weeks train the evaluation model; the final 20% of usable weeks form a rolling one-week-ahead holdout, with each previous simulated actual available for the next row's lag features. The evaluation model is not retrained during that holdout. The baseline is the mean of the previous four simulated actual outputs. After that evaluation is saved, the serving artifact is refit on all 204 usable simulated rows. This does not change the saved holdout predictions or scores.

The MAE and feature-importance values describe only this synthetic dataset and its assumptions. They are not estimates of real MOIL forecast error or proven causal drivers.

## Person 4 prediction handoff

Import `predict_next_week` from `src.forecast_model`. Downtime and blast delay are estimates for the forecast week or what-if controls; they are not observations of future operations. Pass rainfall observed before the target week (or a weather forecast), never the target week's realized rainfall. The function returns both forecasts, gaps, risk bands, the inputs behind the prediction, simulated holdout MAEs, and warnings when an input is outside the synthetic training range.

```python
from src.forecast_model import predict_next_week

result = predict_next_week(
    planned_tonnes=1000,
    rainfall_mm_previous_week=15,
    downtime_hours=8,
    blast_delay_hours=2,
    actual_tonnes_lag_1=930,
    rolling_mean_4=940,
)
print(result)
```

The reported holdout MAEs are 25.89 tonnes for the Random Forest and 36.16 tonnes for the four-week average on 41 simulated holdout weeks. They describe only this generated demo series, not real mine forecasting accuracy.

Risk bands (under 5% low, 5–10% medium, over 10% high) are demo thresholds, not MOIL policy. Any operational recommendation should be a separately explained rule; the model forecast itself is not causal evidence that changing a constraint will recover the displayed tonnes.

## Project documents

- [Final demo implementation plan](SIH26009_final_implementation_plan.md)
- [Four-person work plan](SIH26009_four_person_work_plan.md)
- [Person 3 simulation and handoff notes](data/processed/person3_simulation_notes.md)

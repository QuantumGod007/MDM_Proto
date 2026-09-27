"""Train and serve the simulated one-week-ahead production demo model."""

from __future__ import annotations

import csv
import json
import math
import platform
from pathlib import Path
from typing import Any

import joblib
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "simulated_operations_weekly.csv"
RESULTS_PATH = ROOT / "data" / "processed" / "forecast_results.csv"
METRICS_PATH = ROOT / "data" / "processed" / "forecast_metrics.json"
EXAMPLE_PATH = ROOT / "data" / "processed" / "forecast_example.json"
MODEL_PATH = ROOT / "models" / "random_forest_model.joblib"
SEED = 26009

FEATURES = [
    "planned_tonnes",
    "rainfall_mm_previous_week",
    "downtime_hours",
    "equipment_available_pct",
    "blast_delay_hours",
    "actual_tonnes_lag_1",
    "rolling_mean_4",
]


def _as_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value == "":
        raise ValueError(f"Missing required model input: {key}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Model input must be a finite number: {key}")
    return number


def _new_model() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=300,
        max_depth=5,
        min_samples_leaf=3,
        random_state=SEED,
        n_jobs=-1,
    )


def _shortfall(prediction: float, planned: float) -> tuple[float, float, str]:
    gap = planned - prediction
    percentage = max(0.0, gap / planned * 100.0) if planned > 0 else 0.0
    if percentage < 5.0:
        band = "low"
    elif percentage <= 10.0:
        band = "medium"
    else:
        band = "high"
    return gap, percentage, band


def train_and_evaluate() -> dict[str, Any]:
    with DATA_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    usable = [
        row
        for row in rows
        if all(row.get(feature, "") != "" for feature in FEATURES)
        and row.get("actual_tonnes", "") != ""
    ]
    if len(usable) < 20:
        raise ValueError(f"Need at least 20 usable rows; found {len(usable)}")
    dates = [row["week_start"] for row in usable]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("Usable weeks must be unique and in chronological order")

    split = int(len(usable) * 0.8)
    training_rows = usable[:split]
    holdout_rows = usable[split:]
    x_train = [[_as_float(row, name) for name in FEATURES] for row in training_rows]
    y_train = [_as_float(row, "actual_tonnes") for row in training_rows]
    x_holdout = [[_as_float(row, name) for name in FEATURES] for row in holdout_rows]
    y_holdout = [_as_float(row, "actual_tonnes") for row in holdout_rows]

    evaluation_model = _new_model()
    evaluation_model.fit(x_train, y_train)
    rf_predictions = evaluation_model.predict(x_holdout)
    baseline_predictions = [_as_float(row, "rolling_mean_4") for row in holdout_rows]

    results: list[dict[str, str]] = []
    for row, actual, baseline, rf in zip(
        holdout_rows, y_holdout, baseline_predictions, rf_predictions
    ):
        planned = _as_float(row, "planned_tonnes")
        baseline_gap, baseline_pct, baseline_band = _shortfall(baseline, planned)
        rf_gap, rf_pct, rf_band = _shortfall(float(rf), planned)
        results.append(
            {
                "week_start": row["week_start"],
                "demo_site_id": row.get("demo_site_id", "DEMO-01"),
                "planned_tonnes": f"{planned:.2f}",
                "simulated_actual_tonnes": f"{actual:.2f}",
                "four_week_average_forecast_tonnes": f"{baseline:.2f}",
                "random_forest_forecast_tonnes": f"{float(rf):.2f}",
                "baseline_gap_tonnes": f"{baseline_gap:.2f}",
                "baseline_shortfall_pct": f"{baseline_pct:.2f}",
                "baseline_risk_band": baseline_band,
                "rf_gap_tonnes": f"{rf_gap:.2f}",
                "rf_shortfall_pct": f"{rf_pct:.2f}",
                "rf_risk_band": rf_band,
                "data_status": "simulated_holdout",
            }
        )

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(results[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(results)

    # Keep the reported holdout predictions untouched, then refit the serving
    # artifact on all available demo rows so it can use the full synthetic set.
    all_x = [[_as_float(row, name) for name in FEATURES] for row in usable]
    all_y = [_as_float(row, "actual_tonnes") for row in usable]
    serving_model = _new_model()
    serving_model.fit(all_x, all_y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(serving_model, MODEL_PATH)

    feature_ranges = {
        name: {
            "min": min(_as_float(row, name) for row in usable),
            "max": max(_as_float(row, name) for row in usable),
        }
        for name in FEATURES
    }

    metrics = {
        "target": "simulated actual_tonnes",
        "train_rows": len(training_rows),
        "holdout_rows": len(holdout_rows),
        "train_start": training_rows[0]["week_start"],
        "train_end": training_rows[-1]["week_start"],
        "holdout_start": holdout_rows[0]["week_start"],
        "holdout_end": holdout_rows[-1]["week_start"],
        "split": "chronological 80/20; no shuffling",
        "evaluation_method": (
            "fixed-model rolling one-week-ahead chronological holdout; each prior "
            "simulated actual is available for the next week's lag features"
        ),
        "random_forest_mae_tonnes": round(
            mean_absolute_error(y_holdout, rf_predictions), 2
        ),
        "four_week_average_mae_tonnes": round(
            mean_absolute_error(y_holdout, baseline_predictions), 2
        ),
        "features": FEATURES,
        "feature_importances": {
            name: round(float(value), 4)
            for name, value in zip(FEATURES, serving_model.feature_importances_)
        },
        "feature_importances_scope": "final serving model fit on all usable simulated rows; descriptive only, not causal",
        "serving_model_training_rows": len(usable),
        "serving_model_train_start": usable[0]["week_start"],
        "serving_model_train_end": usable[-1]["week_start"],
        "serving_model_fit_scope": "all usable simulated rows, refit after holdout evaluation",
        "training_feature_ranges": feature_ranges,
        "scikit_learn_version": sklearn.__version__,
        "joblib_version": joblib.__version__,
        "python_version": platform.python_version(),
        "random_seed": SEED,
        "interpretation": (
            "Scores measure performance on simulated holdout rows only; they are not "
            "validated against MOIL production."
        ),
    }
    with METRICS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
        handle.write("\n")

    base_inputs = {
        "planned_tonnes": 1000,
        "rainfall_mm_previous_week": 15,
        "downtime_hours": 8,
        "blast_delay_hours": 2,
        "actual_tonnes_lag_1": 930,
        "rolling_mean_4": 940,
    }
    scenario_inputs = {**base_inputs, "downtime_hours": 4, "blast_delay_hours": 1}
    example = {
        "description": (
            "Illustrative scenarios for fictional DEMO-01. Inputs and production "
            "are simulated; the holdout MAE is not MOIL accuracy."
        ),
        "inputs": base_inputs,
        "forecast": predict_next_week(**base_inputs),
        "scenario_example": {
            "scenario_name": "Reduce assumed downtime from 8 to 4 hours and blast delay from 2 to 1 hour",
            "inputs": scenario_inputs,
            "forecast": predict_next_week(**scenario_inputs),
        },
    }
    with EXAMPLE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(example, handle, indent=2)
        handle.write("\n")
    return metrics


def predict_next_week(
    *,
    planned_tonnes: float,
    rainfall_mm_previous_week: float,
    downtime_hours: float,
    blast_delay_hours: float,
    actual_tonnes_lag_1: float,
    rolling_mean_4: float,
) -> dict[str, Any]:
    """Return demo forecasts for pre-week plans and scenario assumptions.

    Downtime and blast delay are estimates/what-if inputs for the forecast week,
    not observations of future mine operations. All returned performance values
    are based on the simulated historical holdout.
    """
    if planned_tonnes <= 0:
        raise ValueError("planned_tonnes must be greater than zero")
    if not 0 <= downtime_hours <= 168:
        raise ValueError("downtime_hours must be between 0 and 168")
    if blast_delay_hours < 0:
        raise ValueError("blast_delay_hours cannot be negative")

    supplied_inputs = {
        "planned_tonnes": planned_tonnes,
        "rainfall_mm_previous_week": rainfall_mm_previous_week,
        "downtime_hours": downtime_hours,
        "blast_delay_hours": blast_delay_hours,
        "actual_tonnes_lag_1": actual_tonnes_lag_1,
        "rolling_mean_4": rolling_mean_4,
    }
    for name, value in supplied_inputs.items():
        if not math.isfinite(float(value)):
            raise ValueError(f"{name} must be a finite number")
        if name != "planned_tonnes" and float(value) < 0:
            raise ValueError(f"{name} cannot be negative")

    availability = 100.0 * (168.0 - downtime_hours) / 168.0
    risk_inputs = {
        "planned_tonnes": float(planned_tonnes),
        "rainfall_mm_previous_week": float(rainfall_mm_previous_week),
        "downtime_hours": float(downtime_hours),
        "equipment_available_pct": availability,
        "blast_delay_hours": float(blast_delay_hours),
        "actual_tonnes_lag_1": float(actual_tonnes_lag_1),
        "rolling_mean_4": float(rolling_mean_4),
    }
    vector = [[
        float(planned_tonnes),
        float(rainfall_mm_previous_week),
        float(downtime_hours),
        availability,
        float(blast_delay_hours),
        float(actual_tonnes_lag_1),
        float(rolling_mean_4),
    ]]
    model = joblib.load(MODEL_PATH)
    rf_prediction = float(model.predict(vector)[0])
    baseline_prediction = float(rolling_mean_4)
    with METRICS_PATH.open(encoding="utf-8") as handle:
        metrics = json.load(handle)
    range_warnings = [
        f"{name} is outside the simulated training range "
        f"[{bounds['min']:.2f}, {bounds['max']:.2f}]"
        for name, value in risk_inputs.items()
        if (bounds := metrics.get("training_feature_ranges", {}).get(name))
        and not bounds["min"] <= value <= bounds["max"]
    ]
    rf_gap, rf_pct, rf_band = _shortfall(rf_prediction, planned_tonnes)
    baseline_gap, baseline_pct, baseline_band = _shortfall(
        baseline_prediction, planned_tonnes
    )
    return {
        "demo_site_id": "DEMO-01",
        "random_forest_forecast_tonnes": round(rf_prediction, 2),
        "four_week_average_forecast_tonnes": round(baseline_prediction, 2),
        "planned_tonnes": round(float(planned_tonnes), 2),
        "rf_gap_tonnes": round(rf_gap, 2),
        "rf_shortfall_pct": round(rf_pct, 2),
        "rf_risk_band": rf_band,
        "baseline_gap_tonnes": round(baseline_gap, 2),
        "baseline_shortfall_pct": round(baseline_pct, 2),
        "baseline_risk_band": baseline_band,
        "risk_inputs": risk_inputs,
        "input_range_warnings": range_warnings,
        "holdout_random_forest_mae_tonnes": metrics["random_forest_mae_tonnes"],
        "holdout_four_week_average_mae_tonnes": metrics[
            "four_week_average_mae_tonnes"
        ],
        "holdout_evaluation_scope": (
            f"simulated chronological holdout {metrics['holdout_start']} through "
            f"{metrics['holdout_end']}"
        ),
        "data_status": "simulated_demo_model",
    }

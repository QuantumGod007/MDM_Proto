"""Build a reproducible, explicitly simulated operations series for the demo."""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "rainfall_weekly.csv"
OUTPUT = ROOT / "data" / "processed" / "simulated_operations_weekly.csv"
SEED = 26009


def generate() -> int:
    rng = random.Random(SEED)
    with INPUT.open(newline="", encoding="utf-8-sig") as handle:
        rainfall_rows = list(csv.DictReader(handle))

    if not rainfall_rows:
        raise ValueError(f"No rainfall rows found in {INPUT}")

    required = {"week_start", "rainfall_mm", "data_source", "data_status"}
    missing = required.difference(rainfall_rows[0])
    if missing:
        raise ValueError(f"Rainfall file is missing required columns: {sorted(missing)}")

    dates = [row["week_start"] for row in rainfall_rows]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("Rainfall weeks must be unique and in chronological order")

    output_rows: list[dict[str, str]] = []
    previous_actual: float | None = None
    previous_plan: float | None = None
    previous_rainfall: float | None = None
    recent_actuals: list[float] = []

    for index, rain_row in enumerate(rainfall_rows):
        rainfall = float(rain_row["rainfall_mm"])

        # These are synthetic pre-week planning assumptions, not observed MOIL logs.
        annual_cycle = math.sin(2 * math.pi * (index % 52) / 52)
        planned = max(0.0, 1000.0 + 20.0 * annual_cycle + rng.gauss(0, 10.0))
        downtime = min(30.0, max(0.0, rng.triangular(0.0, 30.0, 8.0)))
        blast_delay = min(10.0, max(0.0, rng.triangular(0.0, 10.0, 1.5)))
        availability = 100.0 * (168.0 - downtime) / 168.0

        # Use only rainfall already observed before this simulated week.
        rain_feature = previous_rainfall if previous_rainfall is not None else 0.0
        carryover = 0.0
        if previous_actual is not None and previous_plan is not None:
            carryover = 0.15 * (previous_actual - previous_plan)

        # Illustrative rule for creating a synthetic target. Coefficients are
        # assumptions for the demo, not estimated mine-performance effects.
        actual = (
            planned
            - 2.5 * downtime
            - 8.0 * blast_delay
            - 0.45 * rain_feature
            + carryover
            + rng.gauss(0, 20.0)
        )
        actual = min(planned, max(0.0, actual))

        row = {
            "week_start": rain_row["week_start"],
            "demo_site_id": "DEMO-01",
            "study_area": "Dongri Buzurg Mine demo area, Bhandara, Maharashtra",
            "rainfall_source_site_id": rain_row.get("mine_id", ""),
            "planned_tonnes": f"{planned:.2f}",
            "actual_tonnes": f"{actual:.2f}",
            "rainfall_mm": f"{rainfall:.2f}",
            "rainfall_mm_previous_week": "" if previous_rainfall is None else f"{previous_rainfall:.2f}",
            "downtime_hours": f"{downtime:.2f}",
            "equipment_available_pct": f"{availability:.2f}",
            "blast_delay_hours": f"{blast_delay:.2f}",
            "actual_tonnes_lag_1": "" if previous_actual is None else f"{previous_actual:.2f}",
            "rolling_mean_4": "" if len(recent_actuals) < 4 else f"{sum(recent_actuals[-4:]) / 4:.2f}",
            "rainfall_data_source": rain_row["data_source"],
            "rainfall_data_status": rain_row["data_status"],
            "data_status": "simulated",
            "operations_data_status": "simulated",
            "simulation_seed": str(SEED),
        }
        output_rows.append(row)
        previous_actual = actual
        previous_plan = planned
        previous_rainfall = rainfall
        recent_actuals.append(actual)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(output_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(output_rows)
    return len(output_rows)


if __name__ == "__main__":
    count = generate()
    print(f"Wrote {count} simulated weekly rows to {OUTPUT}")

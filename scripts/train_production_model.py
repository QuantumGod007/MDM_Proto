"""Train the demo Random Forest and create chronological holdout outputs."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.forecast_model import train_and_evaluate


if __name__ == "__main__":
    for name, value in train_and_evaluate().items():
        print(f"{name}: {value}")

import pandas as pd

from reusable_helpers.monitoring.drift.config import DriftMonitorConfig
from reusable_helpers.monitoring.drift.monitor import ModelDriftMonitor

if __name__ == "__main__":
    reference = pd.DataFrame(
        {"value": [1, 2, 3, 4, 5], "category": ["a", "b", "a", "b", "a"]}
    )
    current = pd.DataFrame(
        {"value": [2, 3, 4, 5, 6], "category": ["a", "c", "c", "b", "a"]}
    )
    monitor = ModelDriftMonitor(
        DriftMonitorConfig(
            feature_types={"value": "numerical", "category": "categorical"}
        )
    )
    bins, summary = monitor.calculate_psi(reference, current)
    print(summary.to_string(index=False))

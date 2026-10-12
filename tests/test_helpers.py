import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reusable_helpers.shared.config import parse_bool, parse_list, resolve
from reusable_helpers.workflows.metaflow.airflow import (
    generate_dag,
    get_patch_config,
    patch_config,
)


class ConfigurationTests(unittest.TestCase):
    def test_explicit_values_override_even_invalid_environment(self):
        with patch.dict(os.environ, {"SETTING": "invalid"}):
            self.assertFalse(resolve(False, env="SETTING", parser=parse_bool))
            self.assertEqual(resolve(0, env="SETTING", parser=int), 0)
            self.assertEqual(resolve([], env="SETTING", parser=parse_list), [])
            self.assertIsNone(resolve(None, env="SETTING", default=5))

    def test_environment_and_default(self):
        with patch.dict(os.environ, {"SETTING": "off"}):
            self.assertFalse(resolve(env="SETTING", parser=parse_bool))
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve(env="SETTING", default=3), 3)
            with self.assertRaisesRegex(ValueError, "SETTING is required"):
                resolve(env="SETTING", required=True)


class DagGenerationTests(unittest.TestCase):
    def test_patch_escaping_and_atomic_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "dag.py"
            original = "CONFIG = {'dag_id': 'old', 'tags': ('old',)}\n"
            file.write_text(original)
            with self.assertRaisesRegex(ValueError, "start_date"):
                patch_config(
                    file, get_patch_config(dag_id="new", start_date="2026-01-01")
                )
            self.assertEqual(file.read_text(), original)
            patch_config(file, get_patch_config(dag_id="quote'and\\backslash", tags=[]))
            namespace = {}
            exec(file.read_text(), namespace)
            self.assertEqual(namespace["CONFIG"]["dag_id"], "quote'and\\backslash")
            self.assertEqual(namespace["CONFIG"]["tags"], [])

    def test_generation_failure_keeps_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            flow = Path(directory) / "flow.py"
            flow.write_text("# example\n")
            output = Path(directory) / "dag.py"
            output.write_text("# existing\n")
            with patch(
                "reusable_helpers.workflows.metaflow.airflow.subprocess.run",
                side_effect=RuntimeError("failed"),
            ):
                with self.assertRaises(RuntimeError):
                    generate_dag(flow, output)
            self.assertEqual(output.read_text(), "# existing\n")

    def test_child_environment_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            flow = Path(directory) / "flow.py"
            flow.write_text("# example\n")
            output = Path(directory) / "dag.py"

            def fake_run(command, *, check, env):
                self.assertTrue(check)
                self.assertEqual(env["EXAMPLE_SETTING"], "override")
                self.assertNotIn("--production", command)
                Path(command[command.index("create") + 1]).write_text(
                    "CONFIG = {'dag_id': 'old'}\n"
                )

            with patch(
                "reusable_helpers.workflows.metaflow.airflow.subprocess.run",
                side_effect=fake_run,
            ):
                generate_dag(
                    flow,
                    output,
                    deploy=False,
                    env_overrides={"EXAMPLE_SETTING": "override"},
                    dag_id="example",
                )
            self.assertIn("'example'", output.read_text())
            self.assertNotIn("EXAMPLE_SETTING", os.environ)


try:
    import numpy as np
    import pandas as pd

    from reusable_helpers.monitoring.drift.config import DriftMonitorConfig
    from reusable_helpers.monitoring.drift.monitor import ModelDriftMonitor
except ImportError:
    SCIENTIFIC_DEPENDENCIES = False
else:
    SCIENTIFIC_DEPENDENCIES = True


@unittest.skipUnless(SCIENTIFIC_DEPENDENCIES, "scientific dependencies not installed")
class DriftTests(unittest.TestCase):
    def setUp(self):
        self.monitor = ModelDriftMonitor(
            DriftMonitorConfig(
                feature_types={"value": "numerical", "category": "categorical"}
            )
        )

    def test_identical_populations_are_stable(self):
        frame = pd.DataFrame(
            {"value": [1, 2, 3, np.nan], "category": ["a", "b", "a", None]}
        )
        _, summary = self.monitor.calculate_psi(frame, frame)
        self.assertTrue(np.allclose(summary["psi"], 0))
        self.assertEqual(set(summary["drift_level"]), {"stable"})

    def test_all_missing_reference_and_unseen_categories(self):
        reference = pd.DataFrame({"value": [np.nan, np.nan], "category": ["a", None]})
        current = pd.DataFrame({"value": [1, 2], "category": ["b", "b"]})
        bins, summary = self.monitor.calculate_psi(reference, current)
        self.assertTrue(np.isfinite(summary["psi"]).all())
        self.assertEqual(
            int(bins.loc[bins["bin"] == "__OTHER__", "current_count"].sum()), 2
        )

    def test_empty_populations_fail_clearly(self):
        frame = pd.DataFrame({"value": [1], "category": ["a"]})
        with self.assertRaisesRegex(ValueError, "nonempty"):
            self.monitor.calculate_psi(frame.iloc[:0], frame)

    def test_shap_report_and_incompatible_shape(self):
        frame = pd.DataFrame({"value": [1, 2], "category": ["a", "b"]})
        report = self.monitor.generate_drift_report(
            frame, frame, lambda data: np.ones(data.shape)
        )
        self.assertEqual(report.top_k_overlap["top_k_overlap_ratio"], 1)
        with self.assertRaisesRegex(ValueError, "single-output matrix"):
            self.monitor.calculate_shap_importance(
                frame, lambda data: np.ones((2, 2, 3))
            )

    def test_env_configuration_supports_overrides(self):
        with patch.dict(os.environ, {"DRIFT_MAX_NUMERICAL_BINS": "4"}):
            config = DriftMonitorConfig.from_env(
                feature_types={"x": "numerical"}, max_numerical_bins=2
            )
        self.assertEqual(config.max_numerical_bins, 2)


if __name__ == "__main__":
    unittest.main()

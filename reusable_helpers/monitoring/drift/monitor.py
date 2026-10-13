from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .config import DriftMonitorConfig, FeatureType

MISSING_BIN = "__MISSING__"
OTHER_BIN = "__OTHER__"


@dataclass(frozen=True)
class BinSpec:
    """Frozen bin definition learned from one reference feature."""

    feature_name: str
    feature_type: FeatureType
    labels: Tuple[str, ...]
    edges: Optional[Tuple[float, ...]] = None
    category_tokens: Optional[Tuple[str, ...]] = None


@dataclass(frozen=True)
class DriftReport:
    """Combined output from :meth:`ModelDriftMonitor.generate_drift_report`."""

    psi_bins: pd.DataFrame
    psi_summary: pd.DataFrame
    shap_features: pd.DataFrame
    spearman_correlation: float
    spearman_p_value: float
    top_k_overlap: Mapping[str, Any]


class ModelDriftMonitor:
    """Compare current feature distributions with a reference dataset.

    Configuration is validated by :class:`DriftMonitorConfig`. Reference and
    current populations are supplied directly for each calculation.
    """

    SHAP_FEATURE_COLUMNS = [
        "feature_name",
        "mean_abs_shap_reference",
        "mean_abs_shap_current",
        "reference_rank",
        "current_rank",
    ]

    def __init__(self, config: DriftMonitorConfig) -> None:
        self.config = DriftMonitorConfig.model_validate(config)
        self.feature_types: Dict[str, FeatureType] = dict(self.config.feature_types)

    @staticmethod
    def _category_token(value: Any) -> str:
        return f"category::{type(value).__name__}::{value!r}"

    def generate_bins(self, feature_name: str, series: pd.Series) -> BinSpec:
        """Generate a bin specification from a reference feature."""

        feature_type = self.feature_types[feature_name]

        if feature_type == "numerical":
            numeric = pd.to_numeric(series, errors="raise")
            non_null = numeric.dropna().to_numpy(dtype=float)
            quantiles = np.linspace(0.0, 1.0, self.config.max_numerical_bins + 1)
            if np.isinf(non_null).any():
                raise ValueError(f"{feature_name} contains infinite numerical values")
            edges = (
                np.unique(np.quantile(non_null, quantiles)).astype(float)
                if non_null.size
                else np.array([])
            )
            if edges.size <= 1:
                edges = np.array([-np.inf, np.inf], dtype=float)
            else:
                edges[0] = -np.inf
                edges[-1] = np.inf
            bin_labels = tuple(f"__BIN_{index:03d}__" for index in range(len(edges) - 1))
            return BinSpec(
                feature_name=feature_name,
                feature_type="numerical",
                labels=bin_labels + (MISSING_BIN,),
                edges=tuple(float(edge) for edge in edges),
            )

        # Create "<category>::<type>::<value>" tokens for each value
        category_tokens = tuple(
            sorted({self._category_token(value) for value in series if not pd.isna(value)})
        )
        return BinSpec(
            feature_name=feature_name,
            feature_type="categorical",
            labels=category_tokens + (OTHER_BIN, MISSING_BIN),
            category_tokens=category_tokens,
        )

    def assign_bins(self, spec: BinSpec, series: pd.Series) -> pd.Series:
        if spec.feature_type == "numerical":
            if spec.edges is None:
                raise ValueError("Numerical bins require edges")
            numeric = pd.to_numeric(series, errors="raise")
            labels = list(spec.labels[:-1])
            assigned = pd.cut(
                numeric,
                bins=list(spec.edges),
                labels=labels,
                include_lowest=True,
            ).astype(object)
            assigned[pd.isna(numeric)] = MISSING_BIN
            return pd.Series(assigned, index=series.index, name=series.name)

        if spec.category_tokens is None:
            raise ValueError("Categorical bins require category tokens")
        known = set(spec.category_tokens)

        def assign(value: Any) -> str:
            if pd.isna(value):
                return MISSING_BIN
            token = self._category_token(value)
            return token if token in known else OTHER_BIN

        return series.map(assign)

    def classify_psi(self, psi_value: float) -> str:
        """Classify one total PSI value using the configured thresholds."""
        if psi_value < self.config.psi_warning_threshold:
            return "stable"
        if psi_value < self.config.psi_drift_threshold:
            return "warning"
        return "drift"

    def calculate_psi(
        self, reference_df: pd.DataFrame, current_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Return per-bin PSI details and per-feature PSI totals."""

        if reference_df.empty or current_df.empty:
            raise ValueError("reference and current datasets must both be nonempty")
        reference = reference_df.loc[:, list(self.feature_types)].copy(deep=True)
        specs = {
            feature: self.generate_bins(feature, reference[feature])
            for feature in self.feature_types
        }

        details = []
        summaries = []
        for feature_name, feature_type in self.feature_types.items():
            spec = specs[feature_name]
            reference_bins = self.assign_bins(spec, reference[feature_name])
            current_bins = self.assign_bins(spec, current_df[feature_name])
            reference_counts = reference_bins.value_counts().reindex(spec.labels, fill_value=0)
            current_counts = current_bins.value_counts().reindex(spec.labels, fill_value=0)
            reference_proportions = reference_counts / len(reference_bins)
            current_proportions = current_counts / len(current_bins)
            safe_reference = reference_proportions.clip(
                lower=self.config.psi_zero_proportion_epsilon
            )
            safe_current = current_proportions.clip(lower=self.config.psi_zero_proportion_epsilon)
            difference = reference_proportions - current_proportions
            log_ratio = np.log(safe_reference / safe_current)
            contributions = difference * log_ratio

            if spec.feature_type == "numerical":
                if spec.edges is None:
                    raise ValueError("Numerical bins require edges")
                bin_lower = list(spec.edges[:-1]) + [np.nan]
                bin_upper = list(spec.edges[1:]) + [np.nan]
            else:
                bin_lower = [np.nan] * len(spec.labels)
                bin_upper = [np.nan] * len(spec.labels)

            details.append(
                pd.DataFrame(
                    {
                        "feature_name": feature_name,
                        "feature_type": feature_type,
                        "bin": spec.labels,
                        "bin_lower": bin_lower,
                        "bin_upper": bin_upper,
                        "reference_count": reference_counts.to_numpy(dtype=int),
                        "current_count": current_counts.to_numpy(dtype=int),
                        "proportion_reference": reference_proportions.to_numpy(dtype=float),
                        "proportion_current": current_proportions.to_numpy(dtype=float),
                        "difference": difference.to_numpy(dtype=float),
                        "log_ratio": log_ratio.to_numpy(dtype=float),
                        "psi_contribution": contributions.to_numpy(dtype=float),
                    }
                )
            )
            feature_psi = float(contributions.sum())
            summaries.append(
                {
                    "feature_name": feature_name,
                    "psi": feature_psi,
                    "drift_level": self.classify_psi(feature_psi),
                }
            )

        return (
            pd.concat(details, ignore_index=True),
            pd.DataFrame(summaries, columns=["feature_name", "psi", "drift_level"]),
        )

    # ================================================================
    # SHAP importance calculations
    # ================================================================
    @staticmethod
    def _extract_shap_values(explainer: Any, data: pd.DataFrame) -> np.ndarray:
        explained = explainer(data)
        values = getattr(explained, "values", explained)
        return np.asarray(values)

    def calculate_shap_importance(self, data: pd.DataFrame, explainer: Any) -> pd.DataFrame:
        """Calculate mean absolute SHAP importance for every configured feature."""

        if data.empty:
            raise ValueError("SHAP input must be nonempty")
        feature_frame = data.loc[:, list(self.feature_types)].copy(deep=False)
        values = self._extract_shap_values(explainer, feature_frame)
        expected_shape = feature_frame.shape
        if values.ndim == 1:
            if expected_shape[0] == 1:
                values = values.reshape(1, -1)
            elif expected_shape[1] == 1:
                values = values.reshape(-1, 1)
        if values.ndim != 2 or values.shape != expected_shape:
            raise ValueError(
                "SHAP values must be a single-output matrix with shape "
                f"{expected_shape}; received {values.shape}"
            )
        numeric_values = values.astype(float)
        if not np.isfinite(numeric_values).all():
            raise ValueError("SHAP values must be finite")
        return pd.DataFrame(
            {
                "feature_name": list(self.feature_types),
                "mean_abs_shap": np.mean(np.abs(numeric_values), axis=0),
            }
        )

    def calculate_spearman(
        self,
        reference_importance: np.ndarray,
        current_importance: np.ndarray,
    ) -> Tuple[float, float]:
        """Return Spearman rank correlation and its p-value."""

        if (
            reference_importance.size < 2
            or np.all(reference_importance == reference_importance[0])
            or np.all(current_importance == current_importance[0])
        ):
            return np.nan, np.nan
        result = spearmanr(reference_importance, current_importance)
        return float(result.statistic), float(result.pvalue)

    def calculate_top_k_overlap(
        self,
        reference_importance: np.ndarray,
        current_importance: np.ndarray,
        feature_names: Sequence[str],
    ) -> Mapping[str, Any]:
        """Return deterministic top-k feature overlap details."""

        names = list(feature_names)
        effective_k = min(self.config.shap_top_k, len(names))
        reference_order = np.argsort(-reference_importance, kind="stable")[:effective_k]
        current_order = np.argsort(-current_importance, kind="stable")[:effective_k]
        top_reference = [names[index] for index in reference_order]
        top_current = [names[index] for index in current_order]
        overlap_count = len(set(top_reference).intersection(top_current))
        return {
            "top_k": effective_k,
            "top_k_overlap_count": overlap_count,
            "top_k_overlap_ratio": overlap_count / effective_k,
            "top_reference_features": top_reference,
            "top_current_features": top_current,
        }

    def generate_drift_report(
        self,
        reference_df: pd.DataFrame,
        current_df: pd.DataFrame,
        explainer: Any,
    ) -> DriftReport:
        """Calculate PSI and SHAP stability metrics."""

        psi_bins, psi_summary = self.calculate_psi(reference_df, current_df)
        reference_shap = self.calculate_shap_importance(reference_df, explainer).rename(
            columns={"mean_abs_shap": "mean_abs_shap_reference"}
        )
        current_shap = self.calculate_shap_importance(current_df, explainer).rename(
            columns={"mean_abs_shap": "mean_abs_shap_current"}
        )
        shap_features = reference_shap.merge(current_shap, on="feature_name", validate="one_to_one")
        shap_features["reference_rank"] = (
            shap_features["mean_abs_shap_reference"]
            .rank(method="first", ascending=False)
            .astype(int)
        )
        shap_features["current_rank"] = (
            shap_features["mean_abs_shap_current"].rank(method="first", ascending=False).astype(int)
        )
        shap_features = shap_features[self.SHAP_FEATURE_COLUMNS]
        correlation, p_value = self.calculate_spearman(
            shap_features["mean_abs_shap_reference"].to_numpy(),
            shap_features["mean_abs_shap_current"].to_numpy(),
        )
        overlap = self.calculate_top_k_overlap(
            shap_features["mean_abs_shap_reference"].to_numpy(),
            shap_features["mean_abs_shap_current"].to_numpy(),
            feature_names=tuple(shap_features["feature_name"]),
        )

        return DriftReport(
            psi_bins=psi_bins,
            psi_summary=psi_summary,
            shap_features=shap_features,
            spearman_correlation=correlation,
            spearman_p_value=p_value,
            top_k_overlap=overlap,
        )

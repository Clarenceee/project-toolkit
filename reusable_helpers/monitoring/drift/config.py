from typing import Annotated, Dict, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    field_validator,
    model_validator,
)

from reusable_helpers.shared.config import UNSET, parse_dict, resolve

FeatureType = Literal["numerical", "categorical"]
PositiveStrictInt = Annotated[int, Field(strict=True, ge=1)]
NonNegativeStrictFloat = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
PositiveStrictFloat = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]


class DriftMonitorConfig(BaseModel):
    """Validated configuration for :class:`ModelDriftMonitor`."""

    model_config = ConfigDict(
        frozen=True,
        revalidate_instances="always",
        strict=True,
        validate_default=True,
    )

    feature_types: Dict[StrictStr, FeatureType]
    max_numerical_bins: PositiveStrictInt = 8
    psi_warning_threshold: NonNegativeStrictFloat = 0.10
    psi_drift_threshold: PositiveStrictFloat = 0.25
    psi_zero_proportion_epsilon: PositiveStrictFloat = 1e-10
    shap_top_k: PositiveStrictInt = 10

    @classmethod
    def from_env(cls, **overrides) -> "DriftMonitorConfig":
        """Use explicit values, then DRIFT_* variables, then model defaults."""
        unknown = set(overrides) - set(cls.model_fields)
        if unknown:
            raise ValueError(f"Unknown drift settings: {sorted(unknown)}")
        values = {}
        for name, field in cls.model_fields.items():
            parser = (
                parse_dict
                if name == "feature_types"
                else (int if name in {"max_numerical_bins", "shap_top_k"} else float)
            )
            values[name] = resolve(
                overrides.get(name, UNSET),
                env=f"DRIFT_{name.upper()}",
                default=None if field.is_required() else field.default,
                required=field.is_required(),
                parser=parser,
            )
        return cls(**values)

    @field_validator("feature_types")
    @classmethod
    def validate_feature_types(
        cls, feature_types: Dict[str, FeatureType]
    ) -> Dict[str, FeatureType]:
        if not feature_types:
            raise ValueError("feature_types must contain at least one feature")
        if any(not feature_name for feature_name in feature_types):
            raise ValueError("feature names must not be empty")
        return feature_types

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "DriftMonitorConfig":
        if self.psi_warning_threshold >= self.psi_drift_threshold:
            raise ValueError(
                "thresholds must satisfy psi_warning_threshold < psi_drift_threshold"
            )
        return self

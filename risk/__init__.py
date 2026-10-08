"""
Vigil-X Standalone Unified Risk Engine.

This module provides an explainable, defensible provider risk prioritization
scoring system combining rules, ML, provider anomaly, forward risk, network,
and temporal signals.
"""

from risk.contracts import (
    ConfidenceTier,
    EvidenceTier,
    ProviderScoreRecord,
    RiskTier,
    SignalAvailability,
    SignalComponents,
    SignalContributions,
)


def __getattr__(name: str):
    if name in ("compute_unified_risk", "run_unified_risk", "load_risk_config"):
        import risk.unified_risk as ur
        return getattr(ur, name)
    raise AttributeError(f"module 'risk' has no attribute '{name}'")


__all__ = [
    "compute_unified_risk",
    "run_unified_risk",
    "load_risk_config",
    "ProviderScoreRecord",
    "RiskTier",
    "EvidenceTier",
    "ConfidenceTier",
    "SignalComponents",
    "SignalContributions",
    "SignalAvailability",
]

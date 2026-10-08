"""
Integration wrapper for risk subsystem tests.

Re-exports TestUnifiedRiskEngine from risk/tests/test_unified_risk.py
so that running `pytest` or `pytest -v` from root executes all tests.
"""
from risk.tests.test_unified_risk import TestUnifiedRiskEngine

__all__ = ["TestUnifiedRiskEngine"]

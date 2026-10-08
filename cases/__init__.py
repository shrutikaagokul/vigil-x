"""
Vigil-X Investigation Case Builder Subsystem.

Consolidates multi-signal intelligence into investigator-ready investigation cases.
"""

from cases.contracts import (
    CaseEvidenceRecord,
    CasePriority,
    CaseStatus,
    InvestigationCase,
    NetworkRelationship,
)


def __getattr__(name: str):
    if name in ("build_cases", "run_case_builder", "load_case_config", "generate_case_id"):
        import cases.case_builder as cb
        return getattr(cb, name)
    raise AttributeError(f"module 'cases' has no attribute '{name}'")


__all__ = [
    "build_cases",
    "run_case_builder",
    "load_case_config",
    "generate_case_id",
    "InvestigationCase",
    "CaseEvidenceRecord",
    "CaseStatus",
    "CasePriority",
    "NetworkRelationship",
]

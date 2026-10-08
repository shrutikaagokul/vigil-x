"""
Vigil-X SIU Priority Queue Subsystem.

Provides deterministic, explainable, capacity-aware prioritization of investigation cases.
"""
from siu.contracts import (
    SIUPriorityTier,
    SIUQueueItem,
    SIUQueueStatus,
)


def __getattr__(name: str):
    if name in ("compute_priority_score", "load_queue_config"):
        import siu.priority_engine as pe
        return getattr(pe, name)
    elif name in ("build_siu_queue", "run_siu_pipeline", "generate_evaluation_report"):
        import siu.capacity_optimizer as co
        return getattr(co, name)
    raise AttributeError(f"module 'siu' has no attribute '{name}'")


__all__ = [
    "SIUPriorityTier",
    "SIUQueueStatus",
    "SIUQueueItem",
    "compute_priority_score",
    "load_queue_config",
    "build_siu_queue",
    "run_siu_pipeline",
    "generate_evaluation_report",
]

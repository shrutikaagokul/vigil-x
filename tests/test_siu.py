"""
Test runner hook for the SIU Priority Queue test suites in tests/.
"""

from siu.tests.test_siu_contract import TestSIUContracts
from siu.tests.test_priority_engine import TestPriorityEngine
from siu.tests.test_capacity_optimizer import TestCapacityOptimizer

__all__ = [
    "TestSIUContracts",
    "TestPriorityEngine",
    "TestCapacityOptimizer",
]

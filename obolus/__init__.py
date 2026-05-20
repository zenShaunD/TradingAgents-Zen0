"""
OBOLUS — ZPAK-PRODUCT-004
Autonomous trading and capital allocation system.

This package provides the OBOLUS integration layer on top of TradingAgents-Zen0.
It is the A1 Core Reasoning substrate for the OBOLUS paper-mode shadow observation period.

Classification: TRADE SECRET — ZPAK / Zen Peace AK
Operator: Zen0 (Shaun Dyess)
Phase: PAPER (shadow observation, zero capital at risk)

Public surface:
    from obolus import ObolusConfig, AuditLogger, run_paper_day
"""

from obolus.config import ObolusConfig, PAPER_CONFIG
from obolus.audit import AuditLogger
from obolus.runner import run_paper_day
from obolus.hard_invariants import check_hard_invariants

__version__ = "0.1.0"
__all__ = [
    "ObolusConfig",
    "PAPER_CONFIG",
    "AuditLogger",
    "run_paper_day",
    "check_hard_invariants",
]

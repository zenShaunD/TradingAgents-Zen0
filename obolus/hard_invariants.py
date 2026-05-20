"""
OBOLUS — Hard risk invariants (enforceable assertions).

These 10 invariants are NEVER relaxed.  They are defined in
02-architecture/01.SYSTEM-DESIGN.md and reproduced here as executable
checks that the runner calls before and after every propagate() cycle.

In PAPER mode, all invariants are checked but no position sizing or
execution checks are meaningful (no capital at risk).  The purpose of
checking them in PAPER mode is to ensure the enforcement logic itself
is exercised and debugged before real capital is involved.

Classification: TRADE SECRET — ZPAK / Zen Peace AK
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PortfolioSnapshot:
    """
    Minimal portfolio state required for invariant checks.

    In PAPER mode, all monetary fields are 0.  Populate from broker
    adapter in SHADOW / SCOUT / LIVE modes.
    """
    total_equity: float = 0.0
    daily_pnl: float = 0.0
    positions: Dict[str, float] = None          # ticker → position value
    gross_exposure: float = 0.0
    proposed_kelly_fraction: float = 0.0
    calibrated_confidence: float = 1.0          # MetaKelly output c ∈ [0, 1]
    regime_unknown_probability: float = 0.0     # RegimeSense P(unknown)
    injection_alert: bool = False
    audit_chain_intact: bool = True
    kill_switch_tested: bool = True

    def __post_init__(self):
        if self.positions is None:
            self.positions = {}


@dataclass
class InvariantViolation:
    invariant_id: int
    description: str
    observed: str
    limit: str


def check_hard_invariants(
    snapshot: PortfolioSnapshot,
    mode: str = "PAPER",
) -> List[InvariantViolation]:
    """
    Evaluate all 10 OBOLUS hard invariants against a portfolio snapshot.

    Returns a list of InvariantViolation.  An empty list means all clear.
    In PAPER mode, monetary invariants are vacuously satisfied (equity = 0)
    but logic invariants (injection, audit chain, kill switch) are checked
    against the snapshot flags.

    Parameters
    ----------
    snapshot:
        Current portfolio state.  In PAPER mode use default zeros.
    mode:
        OBOLUS operating mode string.
    """
    violations: List[InvariantViolation] = []

    equity = snapshot.total_equity if snapshot.total_equity > 0 else 1.0  # avoid /0 in PAPER

    # Invariant 1 — Max daily drawdown 2% of total equity
    if snapshot.total_equity > 0:
        drawdown_pct = -snapshot.daily_pnl / snapshot.total_equity
        if drawdown_pct > 0.02:
            violations.append(InvariantViolation(
                invariant_id=1,
                description="Max daily drawdown exceeded",
                observed=f"{drawdown_pct:.2%}",
                limit="2.00%",
            ))

    # Invariant 2 — Max single-position size 5% of equity
    for ticker, value in snapshot.positions.items():
        pct = abs(value) / equity
        if pct > 0.05:
            violations.append(InvariantViolation(
                invariant_id=2,
                description=f"Position size exceeded for {ticker}",
                observed=f"{pct:.2%}",
                limit="5.00%",
            ))

    # Invariant 3 — Max gross leverage 1.5×
    leverage = snapshot.gross_exposure / equity if equity > 0 else 0.0
    if leverage > 1.5:
        violations.append(InvariantViolation(
            invariant_id=3,
            description="Gross leverage cap exceeded",
            observed=f"{leverage:.3f}×",
            limit="1.500×",
        ))

    # Invariant 4 — Kelly fraction cap k ≤ 0.25 (quarter-Kelly)
    if snapshot.proposed_kelly_fraction > 0.25:
        violations.append(InvariantViolation(
            invariant_id=4,
            description="Kelly fraction exceeds quarter-Kelly cap",
            observed=f"{snapshot.proposed_kelly_fraction:.4f}",
            limit="0.2500",
        ))

    # Invariant 5 — Confidence floor: c < 0.6 → position size must be 0
    if snapshot.calibrated_confidence < 0.6 and snapshot.proposed_kelly_fraction > 0.0:
        violations.append(InvariantViolation(
            invariant_id=5,
            description="Position proposed despite confidence below floor",
            observed=f"c={snapshot.calibrated_confidence:.3f}, f={snapshot.proposed_kelly_fraction:.4f}",
            limit="c≥0.60 required for non-zero sizing",
        ))

    # Invariant 6 — Regime uncertainty floor: P(unknown) ≥ 0.4 → block new positions
    if snapshot.regime_unknown_probability >= 0.4 and snapshot.proposed_kelly_fraction > 0.0:
        violations.append(InvariantViolation(
            invariant_id=6,
            description="New position proposed under high regime uncertainty",
            observed=f"P(unknown)={snapshot.regime_unknown_probability:.3f}",
            limit="P(unknown)<0.40 required for new positions",
        ))

    # Invariant 7 — Look-ahead-bias CI (LAB-Fuzz) checked separately in CI;
    # runtime flag placeholder for future LAB-Fuzz integration
    # Not enforced here — enforced by CI gate (A6-LAB-FUZZ)

    # Invariant 8 — Injection monitor: suspicious input → quarantine before trading
    if snapshot.injection_alert:
        violations.append(InvariantViolation(
            invariant_id=8,
            description="TradeInject alert raised — quarantine before trading",
            observed="injection_alert=True",
            limit="injection_alert must be False to proceed",
        ))

    # Invariant 9 — Audit chain must be intact
    if not snapshot.audit_chain_intact:
        violations.append(InvariantViolation(
            invariant_id=9,
            description="Audit chain integrity check failed",
            observed="audit_chain_intact=False",
            limit="audit_chain_intact must be True at all times",
        ))

    # Invariant 10 — Kill switch must have been tested
    if not snapshot.kill_switch_tested:
        violations.append(InvariantViolation(
            invariant_id=10,
            description="Kill switch has not been tested this session",
            observed="kill_switch_tested=False",
            limit="kill_switch_tested must be True before live operation",
        ))

    return violations

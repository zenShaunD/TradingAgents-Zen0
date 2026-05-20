"""
OBOLUS — A1 paper-mode daily runner.

This module implements the daily propagate() loop that constitutes the
Phase 0 shadow observation period.  It is the primary seam between
TradingAgents-Zen0 (signal producer) and the OBOLUS audit chain.

Architectural seam
------------------
    TA-Z0 upstream  │  OBOLUS downstream
    ─────────────────┼──────────────────────────────────
    TradingAgentsGraph.propagate(ticker, date)
                     │  → AuditLogger.log_propagation()
                     │  → check_hard_invariants() (vacuous in PAPER)
                     │  → SHADOW_LOG.jsonl (append-only)
                     │  → traces/{date}_{ticker}.json

In PAPER mode:
    - No capital is at risk.  All fills are simulated.
    - The audit chain is written as if real.
    - Hard invariants are checked against a zero-equity snapshot.
    - Rate-limit guard (12 s sleep) prevents Alpha Vantage free-tier
      exhaustion when data_vendor is alpha_vantage.

Classification: TRADE SECRET — ZPAK / Zen Peace AK
"""

from __future__ import annotations

import os
import time
import logging
from datetime import date as DateType
from typing import Optional, List

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from obolus.config import ObolusConfig, PAPER_CONFIG
from obolus.audit import AuditLogger
from obolus.hard_invariants import check_hard_invariants, PortfolioSnapshot

log = logging.getLogger("obolus.runner")


def run_paper_day(
    analysis_date: Optional[str] = None,
    config: ObolusConfig = PAPER_CONFIG,
    tickers: Optional[List[str]] = None,
) -> dict:
    """
    Execute one full daily A1 shadow observation cycle.

    Iterates over the locked ticker list, calls TradingAgentsGraph.propagate()
    for each, writes an audit record, and sleeps between calls to respect the
    Alpha Vantage free-tier rate limit (5 req/min).

    Parameters
    ----------
    analysis_date:
        Trading date to analyse (YYYY-MM-DD string).  Defaults to today.
    config:
        ObolusConfig instance.  Defaults to the module-level PAPER_CONFIG
        which reads from environment variables.
    tickers:
        Override ticker list.  Defaults to config.tickers.

    Returns
    -------
    dict
        Summary: {"date": ..., "tickers_processed": [...], "record_count": N,
                  "violations": [...]}
    """
    if analysis_date is None:
        analysis_date = DateType.today().isoformat()

    if tickers is None:
        tickers = config.tickers

    config.ensure_dirs()

    # Forward memory log path to TA-Z0 via env (picked up by DEFAULT_CONFIG)
    os.environ["TRADINGAGENTS_MEMORY_LOG_PATH"] = config.memory_log_path

    # Build TA-Z0 config by patching OBOLUS overrides onto DEFAULT_CONFIG
    ta_config = {**DEFAULT_CONFIG, **config.as_ta_config_patch()}

    logger = AuditLogger(
        log_path=config.shadow_log_path,
        traces_dir=config.traces_dir,
        mode=config.mode,
    )

    graph = TradingAgentsGraph(config=ta_config)

    processed: List[str] = []
    all_violations = []

    for i, ticker in enumerate(tickers):
        log.info("[%s] Running %s (%d/%d)…", analysis_date, ticker, i + 1, len(tickers))

        try:
            state, decision = graph.propagate(ticker, analysis_date)
        except Exception as exc:
            log.error("propagate() failed for %s on %s: %s", ticker, analysis_date, exc)
            continue

        # Write audit record — append-only, never mutate
        state_hash = logger.log_propagation(
            ticker=ticker,
            analysis_date=analysis_date,
            state=state,
            decision=decision,
        )
        log.info("[%s] %s → %s  state_hash=%s", analysis_date, ticker,
                 _extract_action(decision), state_hash)

        # Hard invariant check (vacuous in PAPER mode — zero-equity snapshot)
        snapshot = PortfolioSnapshot()
        violations = check_hard_invariants(snapshot, mode=config.mode)
        if violations:
            for v in violations:
                log.warning("INVARIANT #%d VIOLATED: %s", v.invariant_id, v.description)
            all_violations.extend(violations)

        processed.append(ticker)

        # Rate-limit guard — only sleep if more tickers remain
        if i < len(tickers) - 1:
            time.sleep(config.rate_limit_sleep_s)

    total_records = logger.record_count()
    log.info("Run complete. Total audit records: %d", total_records)

    return {
        "date": analysis_date,
        "tickers_processed": processed,
        "record_count": total_records,
        "violations": [
            {"invariant_id": v.invariant_id, "description": v.description}
            for v in all_violations
        ],
    }


def _extract_action(decision) -> str:
    """Best-effort extraction of the action string from a TA-Z0 decision object."""
    if decision is None:
        return "NONE"
    if isinstance(decision, dict):
        return decision.get("action", str(decision))
    if hasattr(decision, "action"):
        return str(decision.action)
    return str(decision)

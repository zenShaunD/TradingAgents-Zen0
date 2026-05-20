#!/usr/bin/env python3
"""
OBOLUS — A1 daily paper-mode runner (CLI entry point).

Usage
-----
    # Single run (today)
    python scripts/a1_paper_run.py

    # Specify date
    python scripts/a1_paper_run.py --date 2026-05-20

    # Override tickers
    python scripts/a1_paper_run.py --tickers NVDA AAPL SPY

    # Verbose logging
    python scripts/a1_paper_run.py --verbose

Cron (daily at 12:30 AM AKDT = 08:30 UTC, Mon–Fri)
---------------------------------------------------
    30 8 * * 1-5 cd ~/TradingAgents-Zen0 && conda run -n obo-paper \
        python scripts/a1_paper_run.py >> ~/.obolus/audit/a1-shadow/cron.log 2>&1

Environment variables (override defaults without code changes)
--------------------------------------------------------------
    OBOLUS_AUDIT_DIR              root audit dir   (default: ~/.obolus/audit)
    OBOLUS_MODE                   PAPER|SHADOW|...  (default: PAPER)
    TRADINGAGENTS_LLM_PROVIDER    ollama|anthropic|openai  (default: ollama)
    TRADINGAGENTS_DEEP_THINK_LLM  qwen3             (default: qwen3)
    TRADINGAGENTS_QUICK_THINK_LLM qwen3:1.7b        (default: qwen3:1.7b)
    TRADINGAGENTS_LLM_BACKEND_URL http://localhost:11434/v1
    ALPHA_VANTAGE_API_KEY         required only if data_vendors = alpha_vantage

Classification: TRADE SECRET — ZPAK / Zen Peace AK
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date as DateType

from obolus.runner import run_paper_day
from obolus.config import PAPER_CONFIG


def _parse_args():
    p = argparse.ArgumentParser(
        description="OBOLUS A1 paper-mode daily runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--date",
        default=None,
        help="Analysis date (YYYY-MM-DD). Defaults to today.",
    )
    p.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Override ticker list. Defaults to config locked list.",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG logging.",
    )
    return p.parse_args()


def main():
    args = _parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S UTC",
        stream=sys.stdout,
    )

    log = logging.getLogger("obolus.a1_paper_run")
    log.info("=" * 60)
    log.info("OBOLUS A1 Paper Run — mode=%s", PAPER_CONFIG.mode)
    log.info("LLM: %s  deep=%s  quick=%s",
             PAPER_CONFIG.llm_provider,
             PAPER_CONFIG.deep_think_llm,
             PAPER_CONFIG.quick_think_llm)
    log.info("Audit log: %s", PAPER_CONFIG.shadow_log_path)
    log.info("=" * 60)

    analysis_date = args.date or DateType.today().isoformat()

    result = run_paper_day(
        analysis_date=analysis_date,
        config=PAPER_CONFIG,
        tickers=args.tickers,
    )

    log.info("-" * 60)
    log.info("Run summary:")
    log.info(json.dumps(result, indent=2, default=str))

    if result["violations"]:
        log.error("HARD INVARIANT VIOLATIONS DETECTED — review before promotion:")
        for v in result["violations"]:
            log.error("  Invariant #%d: %s", v["invariant_id"], v["description"])
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

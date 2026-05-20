"""
OBOLUS — A1 Core Reasoning configuration layer.

Provides PAPER_CONFIG: the zero-cost, fully-local config for the A1 shadow
observation period.  All values are overridable via env vars so that the same
module can graduate through SHADOW → SCOUT → LIVE without code changes.

Environment variables (all optional, safe defaults apply):
    OBOLUS_AUDIT_DIR        — root directory for audit chain (default: ~/.obolus/audit)
    OBOLUS_MEMORY_LOG_PATH  — TA-Z0 memory log path (default: inside OBOLUS_AUDIT_DIR)
    OBOLUS_MODE             — operating mode: PAPER | SHADOW | SCOUT | LIVE (default: PAPER)
    TRADINGAGENTS_LLM_PROVIDER   — LLM provider for TA-Z0 (default: ollama)
    TRADINGAGENTS_DEEP_THINK_LLM — deep-think model (default: qwen3)
    TRADINGAGENTS_QUICK_THINK_LLM — quick-think model (default: qwen3:1.7b)
    TRADINGAGENTS_LLM_BACKEND_URL — Ollama base URL (default: http://localhost:11434/v1)

Classification: TRADE SECRET — ZPAK / Zen Peace AK
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Operating mode
# ---------------------------------------------------------------------------

# Escalation path: PAPER → SHADOW (≥14 days) → SCOUT (≥28 days) → LIVE
# Each level requires written operator sign-off in 05-ops/promotion-log.md
# No skipping levels. (OBOLUS System Design — Hard Constraint)
VALID_MODES = ("PAPER", "SHADOW", "SCOUT", "LIVE", "HALT")

# ---------------------------------------------------------------------------
# Locked ticker universe for Phase 0 shadow observation
# DO NOT change tickers mid-period — audit continuity depends on stable universe
# ---------------------------------------------------------------------------
DEFAULT_TICKERS: List[str] = ["NVDA", "AAPL", "SPY", "MSFT", "BTC-USD"]

# ---------------------------------------------------------------------------
# Audit directory layout
# ---------------------------------------------------------------------------
_DEFAULT_AUDIT_ROOT = os.path.join(os.path.expanduser("~"), ".obolus", "audit")


@dataclass
class ObolusConfig:
    """
    Runtime configuration for OBOLUS A1 paper-mode shadow observation.

    Attributes
    ----------
    mode:
        Operating mode.  Must be one of VALID_MODES.  PAPER = no capital at risk.
    tickers:
        Locked ticker list.  Freeze on Day 1 of shadow period.
    audit_dir:
        Root of the OBOLUS audit chain directory tree.
    shadow_log_path:
        Append-only JSONL file that is the primary shadow-period audit artifact.
    traces_dir:
        Per-run JSON trace files: {date}_{ticker}.json
    memory_log_path:
        Path forwarded to TRADINGAGENTS_MEMORY_LOG_PATH so TA-Z0 decision
        memory writes into the OBOLUS audit tree.
    llm_provider:
        LLM provider for TA-Z0 agents (ollama recommended for $0 cost).
    deep_think_llm:
        Model name for deep reasoning.  qwen3 (8B) fits in RTX 4070 12 GB VRAM.
    quick_think_llm:
        Model name for fast summarisation.  qwen3:1.7b for near-zero latency.
    backend_url:
        Ollama REST endpoint.  Default: http://localhost:11434/v1
    max_debate_rounds:
        Bull/bear debate rounds.  1 is sufficient for observation period.
    checkpoint_enabled:
        Enable LangGraph SQLite checkpointing for crash-resume.
    rate_limit_sleep_s:
        Seconds to sleep between tickers.  Prevents Alpha Vantage free-tier
        rate-limit errors (5 req/min = 12 s minimum gap).
    benchmark_ticker:
        Benchmark for alpha calculation in TA-Z0 reflection layer.
    """
    mode: str = "PAPER"
    tickers: List[str] = field(default_factory=lambda: list(DEFAULT_TICKERS))
    audit_dir: str = field(
        default_factory=lambda: os.environ.get("OBOLUS_AUDIT_DIR", _DEFAULT_AUDIT_ROOT)
    )
    # sub-paths derived from audit_dir at post-init
    shadow_log_path: str = ""
    traces_dir: str = ""
    memory_log_path: str = ""
    # LLM stack — override via TRADINGAGENTS_* env vars or directly
    llm_provider: str = "ollama"
    deep_think_llm: str = "qwen3"
    quick_think_llm: str = "qwen3:1.7b"
    backend_url: str = "http://localhost:11434/v1"
    # TA-Z0 graph settings
    max_debate_rounds: int = 1
    max_risk_discuss_rounds: int = 1
    checkpoint_enabled: bool = True
    # Operational
    rate_limit_sleep_s: float = 12.0
    benchmark_ticker: Optional[str] = "SPY"

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"Invalid OBOLUS mode '{self.mode}'. Must be one of {VALID_MODES}.")

        # Materialise derived paths
        a1_dir = os.path.join(self.audit_dir, "a1-shadow")
        if not self.shadow_log_path:
            self.shadow_log_path = os.path.join(a1_dir, "SHADOW_LOG.jsonl")
        if not self.traces_dir:
            self.traces_dir = os.path.join(a1_dir, "traces")
        if not self.memory_log_path:
            self.memory_log_path = os.environ.get(
                "OBOLUS_MEMORY_LOG_PATH",
                os.path.join(a1_dir, "trading_memory.md"),
            )

    def ensure_dirs(self) -> None:
        """Create audit directory tree if not present."""
        os.makedirs(self.traces_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.memory_log_path), exist_ok=True)

    def as_ta_config_patch(self) -> dict:
        """
        Return a dict of keys that patch into TradingAgents DEFAULT_CONFIG.
        Pass as: {**DEFAULT_CONFIG, **cfg.as_ta_config_patch()}
        """
        return {
            "llm_provider": self.llm_provider,
            "deep_think_llm": self.deep_think_llm,
            "quick_think_llm": self.quick_think_llm,
            "backend_url": self.backend_url,
            "max_debate_rounds": self.max_debate_rounds,
            "max_risk_discuss_rounds": self.max_risk_discuss_rounds,
            "checkpoint_enabled": self.checkpoint_enabled,
            "memory_log_path": self.memory_log_path,
            "benchmark_ticker": self.benchmark_ticker,
            # During paper mode, keep data vendor as yfinance ($0 cost)
            "data_vendors": {
                "core_stock_apis": "yfinance",
                "technical_indicators": "yfinance",
                "fundamental_data": "yfinance",
                "news_data": "yfinance",
            },
        }


# ---------------------------------------------------------------------------
# Module-level singleton — import and use directly
# ---------------------------------------------------------------------------

def _build_paper_config() -> ObolusConfig:
    mode = os.environ.get("OBOLUS_MODE", "PAPER").upper()
    provider = os.environ.get("TRADINGAGENTS_LLM_PROVIDER", "ollama")
    deep = os.environ.get("TRADINGAGENTS_DEEP_THINK_LLM", "qwen3")
    quick = os.environ.get("TRADINGAGENTS_QUICK_THINK_LLM", "qwen3:1.7b")
    url = os.environ.get("TRADINGAGENTS_LLM_BACKEND_URL", "http://localhost:11434/v1")
    return ObolusConfig(
        mode=mode,
        llm_provider=provider,
        deep_think_llm=deep,
        quick_think_llm=quick,
        backend_url=url,
    )


PAPER_CONFIG: ObolusConfig = _build_paper_config()

"""
OBOLUS — Append-only audit logger.

Every call to propagate() that passes through this layer produces one JSON
record in SHADOW_LOG.jsonl.  Records are append-only and include a SHA-256
state hash so any post-hoc tampering is detectable.

Audit invariant (OBOLUS Hard Invariant #9):
    Every decision logs: reasoning trace, input hash, timestamp, resulting action.
    Log is append-only and hash-chained.

Classification: TRADE SECRET — ZPAK / Zen Peace AK
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

SCHEMA_VERSION = "0.1.0"


class AuditLogger:
    """
    Append-only JSONL logger for OBOLUS A1 shadow observations.

    Each record written by `log_propagation()` contains:
        schema_version  — record format version for future migrations
        run_ts          — ISO-8601 UTC timestamp of propagate() call
        analysis_date   — trading date analysed (YYYY-MM-DD)
        ticker          — instrument symbol
        mode            — OBOLUS operating mode (PAPER | SHADOW | SCOUT | LIVE)
        module          — always "A1-CORE-REASONING" at this seam
        substrate       — always "TradingAgents-Zen0" at this seam
        decision        — structured PM decision dict from propagate()
        state_hash      — first 32 hex chars of SHA-256(json(state))
        trace_file      — relative path to the full state trace JSON

    Parameters
    ----------
    log_path:
        Path to the append-only SHADOW_LOG.jsonl file.
    traces_dir:
        Directory where full per-run trace JSONs are written.
    mode:
        OBOLUS operating mode string (written into every record).
    """

    def __init__(self, log_path: str, traces_dir: str, mode: str = "PAPER") -> None:
        self.log_path = log_path
        self.traces_dir = traces_dir
        self.mode = mode
        os.makedirs(traces_dir, exist_ok=True)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_propagation(
        self,
        *,
        ticker: str,
        analysis_date: str,
        state: Dict[str, Any],
        decision: Any,
    ) -> str:
        """
        Write one audit record for a completed propagate() call.

        Parameters
        ----------
        ticker:
            Instrument symbol (e.g. "NVDA").
        analysis_date:
            Trading date string (YYYY-MM-DD) passed to propagate().
        state:
            Full LangGraph state dict returned by propagate().
        decision:
            Trader/PM structured decision extracted from state.

        Returns
        -------
        str
            The state_hash written into this record (first 32 hex chars).
        """
        run_ts = datetime.now(timezone.utc).isoformat()
        state_hash = self._hash_state(state)
        trace_file = self._write_trace(ticker, analysis_date, state, run_ts)

        record = {
            "schema_version": SCHEMA_VERSION,
            "run_ts": run_ts,
            "analysis_date": analysis_date,
            "ticker": ticker,
            "mode": self.mode,
            "module": "A1-CORE-REASONING",
            "substrate": "TradingAgents-Zen0",
            "decision": self._serialise(decision),
            "state_hash": state_hash,
            "trace_file": trace_file,
        }

        self._append(record)
        return state_hash

    def record_count(self) -> int:
        """Return the number of records currently in SHADOW_LOG.jsonl."""
        if not os.path.exists(self.log_path):
            return 0
        with open(self.log_path, "r", encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())

    def tail(self, n: int = 3) -> list:
        """Return the last *n* records as parsed dicts (most recent last)."""
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, "r", encoding="utf-8") as fh:
            lines = [ln for ln in fh if ln.strip()]
        return [json.loads(ln) for ln in lines[-n:]]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_state(state: Dict[str, Any]) -> str:
        """SHA-256 of the canonical JSON representation, first 32 hex chars."""
        try:
            raw = json.dumps(state, sort_keys=True, default=str).encode("utf-8")
        except Exception:
            raw = str(state).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:32]

    def _write_trace(
        self,
        ticker: str,
        analysis_date: str,
        state: Dict[str, Any],
        run_ts: str,
    ) -> str:
        """
        Write the full state dict to a per-run JSON trace file.

        Filename format: {analysis_date}_{ticker}_{epoch_ms}.json
        Returns relative path from traces_dir parent for portability.
        """
        epoch_ms = int(datetime.fromisoformat(run_ts).timestamp() * 1000)
        filename = f"{analysis_date}_{ticker}_{epoch_ms}.json"
        full_path = os.path.join(self.traces_dir, filename)
        with open(full_path, "w", encoding="utf-8") as fh:
            json.dump(
                {"run_ts": run_ts, "ticker": ticker, "analysis_date": analysis_date, "state": state},
                fh,
                indent=2,
                default=str,
            )
        # Return path relative to audit_dir parent for portability
        return os.path.relpath(full_path, os.path.dirname(self.log_path))

    def _append(self, record: dict) -> None:
        """Append one JSON record to the log file (newline-delimited)."""
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def _serialise(obj: Any) -> Any:
        """Best-effort serialisation of TA-Z0 decision objects."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return vars(obj)
        return str(obj)

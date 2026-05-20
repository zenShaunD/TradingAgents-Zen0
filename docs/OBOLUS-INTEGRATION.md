# OBOLUS × TradingAgents-Zen0 Integration

> Classification: TRADE SECRET — ZPAK / Zen Peace AK  
> Module: A1 Core Reasoning (Trading-R1-OPRO)  
> Phase: PAPER — shadow observation, zero capital at risk  
> Version: 0.1.0

---

## What This Is

This document describes the integration seam between **TradingAgents-Zen0** (the signal generation substrate) and **OBOLUS** (the autonomous trading and capital allocation system, ZPAK-PRODUCT-004).

TradingAgents-Zen0 is **not** a peer system to OBOLUS.  It is the **implementation substrate** for OBOLUS Layer 3 (Signal Inputs) and Layer 4 (Core Reasoning — A1).  OBOLUS wraps it.

---

## Architecture Map

```
┌─────────────────────────────────────────────────────────────┐
│                    OBOLUS SYSTEM                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  LAYER 4 — A1 CORE REASONING (Trading-R1-OPRO)      │   │
│  │                                                     │   │
│  │  TradingAgentsGraph.propagate(ticker, date)         │   │
│  │  ├─ Fundamentals Analyst                            │   │
│  │  ├─ Sentiment Analyst      ──┐                      │   │
│  │  ├─ News Analyst            ├─→ A4 RegimeSense input│   │
│  │  ├─ Technical Analyst    ──┘                        │   │
│  │  ├─ Bull Researcher   ─┐                            │   │
│  │  ├─ Bear Researcher    ├─→ OPRO reasoning scaffold  │   │
│  │  ├─ Trader synthesis  ─┘                            │   │
│  │  └─ PM structured decision ──────────────────────── ┼──→│
│  └──────────────────────────────────────────────────── ┘   │
│                         A2 INTERCEPT SEAM ↓                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  A2 MetaKelly — Kelly sizing + hard-invariant check  │   │
│  └──────────────────────────────────────────────────────┘   │
│                              ↓                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  A5 Execution Layer — broker/exchange adapters        │   │
│  └──────────────────────────────────────────────────────┘   │
│                              ↓                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  AUDIT LOG — append-only, SHA-256 hash-chained       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Integration Table

| OBOLUS Module | TA-Z0 Component | Integration Role |
|---|---|---|
| A1 Core Reasoning | `TradingAgentsGraph.propagate()` + Trader/PM agents | TA-Z0 deliberation IS the RMCC ASSESS/REFINE scaffold |
| A2 Risk Gate (MetaKelly) | PM structured-output decision | A2 intercepts PM output; applies calibrated Kelly sizing + hard invariants |
| A3 Chart Reader (CandEval VLM) | Technical Analyst (MACD/RSI tabular) | TA-Z0 provides tabular signals; A3 VLM cross-checks via vision |
| A4 Regime Sensor (RegimeSense) | Sentiment + News Analyst agents | TA-Z0 produces raw LLM uncertainty signals; A4 fuses via Bayesian MSM |
| A5 TradeInject defense | `tradingagents/dataflows/` news pipeline | A5 wraps TA-Z0 news ingestion for adversarial injection defense |
| A6 LAB-Fuzz CI gate | `tradingagents/dataflows/` temporal logic | Primary look-ahead leakage surface; A6 fuzzes pre-deploy |

---

## OBOLUS RMCC Micro-Cycle Mapping

Every trading decision executes an RMCC micro-cycle.  TA-Z0 covers the first three steps:

```
OBSERVE → TA-Z0 Analyst team (Fundamentals, Sentiment, News, Technical)
ASSESS  → TA-Z0 Bull/Bear Researcher debate + Trader synthesis
REFINE  → TA-Z0 PM structured-output decision
VALIDATE → OBOLUS A2 MetaKelly intercept (Kelly + 10 hard invariants)
EVOLVE  → OBOLUS A5 Execution layer → Audit log
```

---

## What TA-Z0 Does NOT Cover (OBOLUS Owns 100%)

- **A2 MetaKelly** — calibrated Kelly sizing + Brier score drift monitor + Platt scaling bootstrap
- **A4 Bayesian MSM** — regime state vector (TA-Z0 outputs signals, not a probabilistic regime classifier)
- **A5 broker/exchange adapters** — TA-Z0 is simulate-only
- **A6 LAB-Fuzz CI gate** — no look-ahead-bias enforcement in TA-Z0
- **A7 DeFi harness** — Tier-3, future
- **A8 CrossOmega meta-policy** — portfolio-level risk budget
- **PiT data enforcement** — Norgate/Databento/Massive stack (TA-Z0 uses yfinance/Alpha Vantage)

---

## File Layout (This Branch)

```
TradingAgents-Zen0/
├── obolus/
│   ├── __init__.py          — public surface: ObolusConfig, AuditLogger, run_paper_day
│   ├── config.py            — PAPER_CONFIG singleton + ObolusConfig dataclass
│   ├── audit.py             — append-only JSONL audit logger + SHA-256 state hashing
│   ├── runner.py            — daily propagate() loop with rate-limit guard
│   └── hard_invariants.py   — 10 OBOLUS hard invariants as executable assertions
├── scripts/
│   └── a1_paper_run.py      — CLI entry point (cron-ready)
├── docs/
│   └── OBOLUS-INTEGRATION.md — this file
└── .env.obolus.example      — zero-cost env template
```

---

## Phase 0 — Shadow Observation Quickstart

### 1. Environment

```bash
conda create -n obo-paper python=3.13 -y
conda activate obo-paper
cd ~/TradingAgents-Zen0
git checkout obolus/a1-shadow-integration
pip install -e .
```

### 2. Ollama (local LLM, $0)

```bash
ollama pull qwen3
ollama pull qwen3:1.7b
ollama serve          # binds to localhost:11434
```

### 3. Environment file

```bash
cp .env.obolus.example .env
# No edits required for $0 local-only run
```

### 4. First run

```bash
python scripts/a1_paper_run.py --verbose
```

### 5. Verify audit chain

```bash
wc -l ~/.obolus/audit/a1-shadow/SHADOW_LOG.jsonl
tail -n 3 ~/.obolus/audit/a1-shadow/SHADOW_LOG.jsonl | python3 -m json.tool
```

### 6. Cron (daily at 12:30 AM AKDT)

```cron
30 8 * * 1-5 cd ~/TradingAgents-Zen0 && conda run -n obo-paper python scripts/a1_paper_run.py >> ~/.obolus/audit/a1-shadow/cron.log 2>&1
```

---

## 14-Day Promotion Gate

All 7 items must be TRUE before promotion to Phase 1 (A2 calibration).
Sign off in `05-ops/promotion-log.md` in the OBOLUS spec repo.

```
[ ] ≥14 trading days consecutive, no unresolved audit gaps
[ ] SHADOW_LOG.jsonl intact — no missing entries, all have state_hash
[ ] trading_memory.md contains TA-Z0 reflections for each ticker
[ ] Action distribution non-degenerate (not >80% identical)
[ ] At least one checkpoint resume tested and succeeded
[ ] OPERATOR_NOTES.md contains ≥5 qualitative observations
[ ] No hard-invariant breach logic paths observed
```

---

## Hard Risk Invariants (Non-Negotiable)

All 10 invariants are defined in `obolus/hard_invariants.py` and enforced at every propagate() call.  In PAPER mode, monetary invariants are vacuously satisfied (zero equity).  Logic invariants (injection alert, audit chain, kill switch) are always enforced.

| # | Invariant | Limit |
|---|---|---|
| 1 | Max daily drawdown | 2% of equity |
| 2 | Max single-position size | 5% of equity |
| 3 | Max gross leverage | 1.5× |
| 4 | Kelly fraction cap | k ≤ 0.25 |
| 5 | Confidence floor | c ≥ 0.60 for non-zero sizing |
| 6 | Regime uncertainty floor | P(unknown) < 0.40 for new positions |
| 7 | Look-ahead-bias CI | LAB-Fuzz must pass (A6 CI gate) |
| 8 | Injection monitor | TradeInject clear before trading |
| 9 | Audit chain | Append-only, hash-chained, always intact |
| 10 | Kill switch | Tested weekly, 1-second HALT |

---

*OBOLUS — Zen Peace AK / ZPAK — TRADE SECRET — ZPAK-PRODUCT-004*  
*Integration spec v0.1.0 — 2026-05-20*

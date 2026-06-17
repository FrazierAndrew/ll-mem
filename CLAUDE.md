# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set OPENAI_API_KEY in .env.
python seed.py          # seeds 25 mock conversations + analysis into portrait.db
uvicorn main:app --reload
```

## Architecture

Four-tier progressive portrait engine built on FastAPI + SQLite.

### Analysis tiers (engine.py)

| Tier | Trigger | Input | Output |
|------|---------|-------|--------|
| T1 | Every conversation | Single conversation | Atomic metadata (mood, energy, topics, implicit needs) |
| T2 | Every 5 conversations | Last 5 T1 atoms + prior T2 output | Behavioral pattern clusters |
| T3 | Every 15 conversations | All T2 patterns + existing portrait | Full portrait narrative synthesis |
| T4 | Every 10 conversations (≥20) | Portrait + last 10 T1 atoms | Drift detection against baseline |

The key design: each tier's system prompt includes the output of all lower tiers as context, so analysis compounds rather than resets.

### DB schema (portrait.db)

- `conversations` — user/assistant pairs
- `analyses` — all tier outputs keyed by `(conversation_id, tier)`; tier ∈ {t1, t2, t3, t4}
- `portrait` — single row (id=1), updated in-place at T3 runs; version increments each synthesis

### API endpoints

- `POST /chat` — sends message, gets response, triggers appropriate analysis tiers
- `GET /portrait` — current portrait JSON
- `GET /insights` — latest T2 pattern batch + latest T4 drift report

### Frontend (static/index.html)

Three-tab right panel: Portrait / Patterns / Drift. Populated on page load and after each chat message. A tier badge flashes in the header when T2/T3/T4 runs.

### seed.py

Seeds mock data without calling the OpenAI API. Deletes existing `portrait.db` on each run. After seeding, the app starts with 25 conversations, 5 T2 pattern batches, 1 T3 portrait (built at conversation 15), and 1 T4 drift report (built at conversation 20). Real model calls begin for conversation 26 onward.

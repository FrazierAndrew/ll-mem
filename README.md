# ll-mem

What I really want is an LLM that occasionally notices something I haven’t...“you’ve become more pessimistic over the past six months”, \


## Capture Tiers:

| Tier | Trigger | Purpose |
|------|---------|---------|
| T1 | Every conversation | Extract mood, energy, topics, question type, notable phrases, and implicit needs. |
| T2 | Every 5 conversations | Cluster repeated patterns from recent T1 outputs and prior pattern batches. |
| T3 | Every 15 conversations | Synthesize or update the main portrait from accumulated patterns. |
| T4 | Every 10 conversations, after conversation 20 | Compare recent atoms against the established portrait and flag drift. |

## Project structure

```text
.
├── main.py              # FastAPI app and chat endpoints
├── engine.py            # Progressive analysis prompts and tier runners
├── db.py                # SQLite connection and query helpers
├── seed.py              # Demo data loader, no OpenAI calls
├── static/index.html    # Single-page UI
├── requirements.txt
└── .env.example
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`.

## Run with demo data

`seed.py` creates `portrait.db` with mock conversations and precomputed analysis
outputs. It does not call the OpenAI API.

```bash
python seed.py
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`.

The seeded UI starts with 25 conversations, 5 pattern batches, 1 portrait, and 1
drift report. Sending a new chat message will make real OpenAI calls.

## API

- `GET /` - frontend
- `GET /health` - basic health check
- `POST /chat` - send a message, store the exchange, and run analysis tiers
- `GET /portrait` - current portrait JSON
- `GET /insights` - latest pattern batch and latest drift report

Example chat request:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"I keep overthinking work decisions after I make them."}'
```

## Notes for publishing

- Runtime data is intentionally ignored: `.env`, `portrait.db`, and other local
  SQLite files should not be committed.
- The app uses `gpt-4o-mini` in `main.py` and `engine.py`.
- `PORTRAIT_DB_FILE` can point to a different SQLite path if needed.

from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field

from db import (
    get_conn,
    init_db,
    save_conversation,
    get_conversation_count,
    get_portrait,
    get_analyses_by_tier,
)
from engine import PortraitEngine

engine = PortraitEngine()

CHAT_SYSTEM = """\
You are a thoughtful, knowledgeable assistant. Respond helpfully and concisely.\
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_conn() as conn:
        init_db(conn)
    yield


app = FastAPI(title="Portrait Lab", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


@lru_cache
def get_openai_client():
    try:
        return OpenAI()
    except OpenAIError as exc:
        raise HTTPException(
            status_code=500,
            detail="OpenAI client is not configured. Set OPENAI_API_KEY and restart the app.",
        ) from exc


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/chat")
async def chat(req: ChatRequest):
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CHAT_SYSTEM},
                {"role": "user", "content": req.message},
            ],
        )
    except OpenAIError as exc:
        raise HTTPException(status_code=502, detail="OpenAI request failed.") from exc
    answer = response.choices[0].message.content

    with get_conn() as conn:
        conv_id = save_conversation(conn, req.message, answer)
        count = get_conversation_count(conn)
        try:
            engine.after_conversation(conv_id, conn, client)
        except OpenAIError as exc:
            raise HTTPException(status_code=502, detail="OpenAI analysis request failed.") from exc
        tiers_run = _tiers_run_at(count)

    return {"response": answer, "conversation_count": count, "tiers_run": tiers_run}


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/portrait")
async def portrait():
    with get_conn() as conn:
        p = get_portrait(conn)
        count = get_conversation_count(conn)
    return {"portrait": p, "conversation_count": count}


@app.get("/insights")
async def insights():
    with get_conn() as conn:
        t2_batches = get_analyses_by_tier(conn, "t2")
        t4_reports = get_analyses_by_tier(conn, "t4")
        count = get_conversation_count(conn)
    return {
        "conversation_count": count,
        "latest_patterns": t2_batches[-1] if t2_batches else None,
        "pattern_batch_count": len(t2_batches),
        "latest_drift": t4_reports[-1] if t4_reports else None,
    }


def _tiers_run_at(count):
    tiers = ["t1"]
    if count % 5 == 0:
        tiers.append("t2")
    if count % 15 == 0:
        tiers.append("t3")
    if count % 10 == 0 and count >= 20:
        tiers.append("t4")
    return tiers

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from rag.answer import answer_query

app = FastAPI()

# The URL is public and each question spends Anthropic credit, so: a per-IP limit, plus a global ceiling that
# does not depend on knowing the IP at all. get_remote_address reads request.client.host; behind Render's proxy
# run uvicorn with --proxy-headers --forwarded-allow-ips so that holds the real client IP, not the proxy's.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def too_many(request: Request, exc: RateLimitExceeded):
    return JSONResponse({"detail": "Too many questions. Try again later."}, status_code=429)


class Ask(BaseModel):
    question: str = Field(min_length=3, max_length=300)


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ask")
@limiter.limit("200/hour", key_func=lambda request: "everyone")
@limiter.limit("10/minute")
def ask(request: Request, body: Ask):
    try:
        result = json.loads(answer_query(body.question))
    except Exception:
        raise HTTPException(status_code=502, detail="The answer service failed. Try again.")
    return {"question": body.question, **result}

# ask-my-filings

RAG over Indian company filings (quarterly results and earnings-call transcripts for 11 large caps), with retrieval **measured** instead of eyeballed: 30 labelled questions, recall@5, MRR, faithfulness, a refusal set the system must decline, and a head-to-head against stuffing whole filings into a long-context model.

Ask "what revenue growth guidance did Infosys give?" and get a cited answer, or "Not disclosed in the filings I have." when the filings never said.

## Results

30 questions: 24 answerable, 6 unanswerable. Haiku 5.5 answers. Full method, per-question detail and caveats are in [EVAL.md](EVAL.md).

| Metric | Baseline | Final config |
|---|---|---|
| **recall@5** (right chunk in top 5) | 14/24 = 0.58 | **19/24 = 0.79** |
| **MRR** | 0.42 | **0.42** (dipped to 0.39 mid-way, recovered) |
| recall@5: table / note / prose | 5/8, 6/6, 3/10 | **8/8, 6/6, 5/10** |
| **Refusal** (unanswerable questions declined) | 6/6 | **6/6** |
| **Faithfulness** (answered questions, LLM judge) | 14/16 | **16/18 = 0.89** |
| Questions answered (of 24 answerable) | 16 | 18 |

**What moved recall from 0.58 to 0.79:** one change, a context line prepended to each chunk *before embedding* (`Tata Consultancy Services (TCS) | FY27-Q2, quarter ended September 2026 | earnings call transcript`). Every one of the 10 baseline misses had a chunk containing the answer, but that chunk never said which company or quarter it came from, so a question naming "TCS" or "September 2026" had nothing to match. Adding the company and quarter fixed the routing (0.58 to 0.75); adding the calendar period, so "quarter ended September 2026" matches, fixed the rank slips it caused (MRR back to 0.42, table recall to 8/8).

### Did RAG beat long-context? No, on accuracy. It was ~18x cheaper.

| | RAG | Long-context (whole filing in the prompt) |
|---|---|---|
| Answer contains expected string | 15/24 | **24/24** |
| Refusal | 6/6 | 6/6 |
| Cost per question | **$0.0005** | $0.0096 (no caching), $0.0106 (caching) |
| Median latency | 2.1 s | 1.9 s |
| Prompt tokens per question (median / max) | 4.4k / 5.2k | 36k / 274k |

I ran the long-context side by hand (a throwaway script, not kept in this repo) and checked the answers myself, so this one comparison cannot be reproduced from the repo; the method is written out in [EVAL.md](EVAL.md).

This is the best case for long-context: it is told which filing holds the answer, which RAG had to find itself, and the whole corpus (~2.7M tokens) would not fit in one prompt. About 3 of the 9 questions only long-context "won" are right RAG answers worded differently from the strict check, so the real gap is nearer 24 vs 18. Prompt caching made long-context ~10% *more* expensive (most filings are asked about once). Details, assumptions and the INR conversion are in [EVAL.md](EVAL.md).

## How it works

```
question -> embed (bge-small dense + BM25 sparse) -> Qdrant hybrid search (RRF fusion) -> top 5 chunks
         -> Claude Haiku 5.5 (structured output: answerable, answer, cited chunk ids) -> answer, or refusal
```

| Choice | Value | Why |
|---|---|---|
| Chunking | recursive split, **500 tokens, 30 overlap**, counted with bge's own tokenizer | bge-small embeds at most 512 tokens; counting in characters or another tokenizer silently truncates the tail of chunks. 500 leaves room for bge's special tokens |
| Top-k | **5** | Keeps the answer prompt at ~4k tokens. Not tuned: k=10 was not tested, so the 0.79 is recall at 5 specifically |
| Search | **hybrid** dense + BM25, fused with RRF | Filings are full of exact tokens (tickers, "Q2 FY27", figures) that BM25 matches and dense vectors blur |
| Index | Qdrant (HNSW) | At 6,439 chunks forcing exact search returned the same top 5 on 30/30 queries at the same latency, so the index changes nothing at this size; chosen for built-in hybrid. Revisit HNSW parameters past ~100k chunks |
| Refusal | a first-class field (`answerable`) in the model's structured output | Retrieval always returns something, even for unanswerable questions, so refusal can only come from the answer step |

## What did not work or is still weak

- **Tables get cut from their column headers**, and `pypdf` damages numbers (stray spaces, dropped decimals, "Q2" read as "02"). Measured and written up, not fixed.
- **Tie-breaking bug found and fixed:** RRF scores tie often and Qdrant ordered ties randomly, so identical queries gave different rankings (5 orderings in 6 runs), which would have made MRR change between identical runs. Fixed by sorting on `(-score, chunk_id)`.
- **Answers are not deterministic**: the SDK exposes no `temperature` for this model, so answer metrics move by 1-2 questions between runs. Retrieval metrics are exact.
- **The question set is small (30)** with every expected string verified against the filing text. Treat the numbers as indicative, not tight.

## Corpus

91 filings, 11 companies (Reliance, Bharti Airtel, Jio Platforms, HDFC Bank, ICICI Bank, SBI, TCS, Bajaj Finance, LIC, Infosys, NSE), five quarters (FY26-Q2 to FY27-Q2), as `data/filings/TICKER/FYxx-Qn/<kind>-<NEWSID>.txt` plus a `.json` sidecar. Source is BSE announcements.

- BSE often files the same PDF twice under two IDs; duplicates are removed by hashing the extracted text.
- NSE and Jio Platforms are recent listings, so they have one quarter each.

## Run it

Needs Python 3.12 (onnxruntime has no wheels for 3.15 yet; the fastembed install fails there), Node for promptfoo, a Qdrant Cloud cluster, and an Anthropic API key.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && npm install
cp .env.example .env            # ANTHROPIC_API_KEY, QDRANT_URL, QDRANT_API_KEY

python -m rag.store             # chunk, embed and index into Qdrant (a few minutes)
python -m rag.answer            # ask the questions in rag/answer.py
uvicorn app:app --reload        # web UI at http://localhost:8000: question, retrieved chunks (cited ones marked), model answer
PROMPTFOO_PYTHON=.venv/bin/python npx promptfoo eval --no-cache -o output/eval.json
```

`--no-cache` matters: promptfoo caches provider output, so after re-indexing you would otherwise score stale results.

### Deploying (not deployed yet; untested on Render)

`app.py` is a FastAPI app (`POST /ask`, `GET /health`, the page in `static/`). For a Render web service:

- Build command `pip install -r requirements-deploy.txt` (the query path only: no collector, chunking or tokenizer packages).
- Start command `uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'`. Behind Render's proxy the app would otherwise see the proxy's address for every visitor; these flags make uvicorn take the real client IP from `X-Forwarded-For`. `'*'` means "trust that header from any sender", which is only safe because the app is reachable only through Render's proxy. Render's docs on which `X-Forwarded-For` entry is authoritative were not conclusive when I checked, so treat per-IP limiting as best-effort.
- Environment: `ANTHROPIC_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, and `PYTHON_VERSION` set to a 3.12 release.
- The app only reads the existing Qdrant index; it never builds or deletes it.
- The URL is public and spends your Anthropic credit. `slowapi` limits each client IP to 10 questions a minute and the whole service to 200 an hour (a ceiling that does not depend on knowing anyone's IP), and questions are capped at 300 characters. Also set a spend limit in the Anthropic console. Free-tier memory (~512 MB) and cold starts (two models load at import) are the things to watch.

## Layout

```
app.py      FastAPI app + static/index.html (the UI)
rag/        chunk.py (the chunking decision) · embed.py · store.py (index + the index-choice note) · retrieve.py · answer.py
evals/      questions.yaml · answer_provider.py · assert_retrieval.py (recall@5, MRR) · assert_answer.py (refusal, citations)
data/       the filings
EVAL.md     every experiment, with its config and numbers
```

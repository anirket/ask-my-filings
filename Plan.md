# ask-my-filings: Plan

## What we're building

**Two things, and the first one is three hours of plumbing that three later weeks depend on.**

**1. `collector` — a pipeline that quietly accumulates Indian company filings from now until February.** No LLM, no cleverness. Pull announcements and results for 10–12 listed companies you actually follow, store the raw text with ticker, quarter and date, and put it on a schedule that keeps running whether or not you remember it exists.

**2. `ask-my-filings` — RAG over that corpus, with its retrieval actually measured.** Ask "what did Reliance say about capex guidance last quarter?" and get an answer with the exact cited snippet, or an honest refusal when the filing never said.

```
                 ┌──────────────────────────────────────────┐
  BSE/NSE  ──►   │ collector (GitHub Actions, nightly cron) │
                 │  backfill 4 quarters, then incremental   │
                 │  idempotent · run log · retries          │
                 └────────────────┬─────────────────────────┘
                                  ▼  data/filings/*.txt
                 ┌──────────────────────────────────────────┐
  question ──►   │ chunk ─► embed ─► Qdrant ─► retrieve      │
                 │   ─► grade chunks ─► rewrite + retry?     │
                 │   ─► rerank ─► answer with citations      │
                 │   ─► or refuse                            │
                 └────────────────┬─────────────────────────┘
                                  ▼
                      30-question eval: recall@5 · MRR ·
                      faithfulness · refusal rate
                                  ▼
                      vs. long-context baseline: same 30 Qs,
                      whole docs stuffed in. Who wins, and at what ₹?
```

**The part that makes it worth talking about: you measure retrieval, not vibes.** Almost everyone who builds RAG judges it by reading a few answers and nodding. You will have recall@5 and MRR on 30 labelled questions, a faithfulness score, a refusal set the system must *decline*, and a verdict on whether RAG beat just stuffing the documents into a long-context model. "I built RAG" is a bullet point. "My recall@5 was 0.71 at chunk size 512, 0.83 once I stopped splitting tables from their headers, and long-context beat both on accuracy but cost 14× more" is a conversation.

**Why filings and not a pile of PDFs you downloaded:** three different structures in one document — tables, MD&A prose, numbered notes — that each chunk differently, so you have to make a real decision and defend it. And unanswerable questions come free: ask for guidance a company never gave, and the correct behaviour is to refuse.

**What you end up with:**
- **`ask-my-filings`**: public repo, live URL, README leading with the metrics table
- **A corpus that grows on its own** until Week 12 needs it for the fine-tuning dataset
- **`EVAL.md`**: the four metrics, the chunking decision and why, and the RAG-vs-long-context verdict

**Done when:**
- [ ] The collector has run on schedule at least 3 nights in a row without you touching it
- [ ] Live URL, works for a stranger
- [ ] recall@5, MRR, faithfulness and refusal rate written down for your final config, with the before/after rerank delta
- [ ] The rescue count for the self-correcting retry, however unimpressive it is
- [ ] The RAG-vs-long-context verdict, with ₹ and latency alongside accuracy
- [ ] You can defend your chunk size, your top-k and your index choice with reference to how filings are actually structured

**6 days, Nov 9 → Nov 14. All six are build days. There is no backup day.** Nov 9–13 are weekday evenings at ~3.5 hrs; Nov 14 is a Saturday and carries the heaviest load.


---

## Scoreboard (fill in as you go)

| | Your guess | Actual |
|---|---|---|
| Filings in the backfill after Day 1 | *write it Monday morning* | |
| recall@5 on your **first** chunking attempt | | |
| recall@5 on your final config | | |
| recall@5 after reranking | | |
| MRR, final | | |
| Chunking strategies it took | | |
| How often the query rewrite rescues an answer (out of 30) | | |
| Does long-context beat RAG on accuracy? (y/n) | | |
| ₹ per question — RAG vs long-context | | |
| Unanswerable questions correctly refused (out of 6) | | |
| ₹ spent on the whole week | | |

Guess before you measure. Being wrong is the interesting part, and "I expected 0.9 and got 0.6" is a better story than a number with no prediction attached.

---

## Decisions made up front

| Choice | Pick | Why |
|---|---|---|
| Where the collector runs | **GitHub Actions scheduled workflow** | Free, gives you a run log for nothing, and — the actual reason — **it survives you changing laptops**, which you are about to do. A cron on a machine you're replacing in three weeks is not a pipeline |
| Where filings are stored | **Committed to the repo as `.txt`** under `data/filings/TICKER/YYYY-QN/<kind>-<NEWSID>.txt` + a `.json` sidecar (headline, date, category, PDF url) | A quarter has *several* filings (results, investor presentation, call transcript), so the key is BSE's `NEWSID`, not the quarter. A few hundred text files is tens of MB. Object storage is the grown-up answer and it is not worth the setup this week |
| Source | **`bse` package only** (`bse==3.3.4`, pinned — see Sunday). **No NSE.** | `announcements` paginates, so one code path does both backfill and incremental. NSE's RSS is a rolling window that can't backfill, and NSE blocks datacenter IPs — which is what GitHub Actions runs on. Your large-caps are dual-listed, so BSE coverage is complete for this corpus |
| Vector DB | **Qdrant**, local via Docker | Hybrid search built in, so BM25 + dense is a config change rather than a project |
| Embeddings | **Local, `sentence-transformers` + `BAAI/bge-small-en-v1.5`** | Free, no second API key, runs on CPU, ~130MB. Also teaches you that an embedding model is just a model you can run — which matters in Week 8 |
| Answering model | `claude-haiku-5-5` | Same as every other week. Cost comparisons stay comparable |
| Index | **Your call, Day 3. Write the reason down.** | HNSW vs IVFFlat is a question hiring guides name specifically. Twenty minutes of reading, one line of defence |
| Deploy | **Day 4, thin and early** — Render or Railway | You have three repos and zero live URLs. Deploy before it's finished, then keep pushing to it. Cloud Run comes in Week 9 |
| Reranker | **Local cross-encoder** (`ms-marco-MiniLM-L-6-v2`), Day 6 | Free, and usually the biggest single recall jump after chunking. Measured before and after, it's a row in your table rather than a claim |

```
ask-my-filings/
  collector/
    fetch.py            # bse → raw text, idempotent
    schedule.py         # backfill vs incremental
    runlog.py           # what was fetched, what failed, when
  data/filings/TICKER/YYYY-QN/<kind>-<NEWSID>.txt   (+ .json sidecar)
  rag/
    chunk.py            # the decision that matters most
    embed.py            # bge-small, local
    store.py            # Qdrant: index choice lives here
    retrieve.py         # search → rerank (Nov 14) → top-k
    answer.py           # cite or refuse
  evals/
    questions.yaml      # 30 questions: 24 answerable, 6 unanswerable
    metrics.py          # recall@k, MRR, faithfulness
    longcontext.py      # the baseline that might beat you
  app.py                # FastAPI + a thin page, hover reveals the snippet
  .github/workflows/collect.yml
  EVAL.md  README.md  .env.example  requirements.txt
```

---

## Before Day 1 · ~20 min (Sunday Nov 8, between festival things)

- `pip install bse==3.3.4` and confirm it imports. If the package is broken or the API has moved, you want to know Sunday, not at 9pm Monday
- ⚠️ **Pin it — `bse==3.3.4`, not `-U`.** Audited clean on Nov 6: 1,733 lines, no `eval`/`exec`/`subprocess`/`base64`, stdlib + `requests` + `mthrottle` only, and the sole network destination is `api.bseindia.com`. But it's a single-maintainer package with ~80 stars, which is precisely the profile where a compromised account ships a bad release — and your scheduled Action would pull it at 1am without you looking. Pin the version, and pin `mthrottle` too. It is GPL-3.0, so say so in your README
- Create the empty `anirket/ask-my-filings` repo
- **`.env` in `.gitignore` before the first commit.** Same rule as always — the repo is public
- Docker running, so `docker run qdrant/qdrant` works on Day 3 without a detour
- Pick your 10–12 companies. Ones you actually follow, because you'll be writing eval questions about them from memory on Day 5

| Day | Name | You'll walk away with |
|---|---|---|
| 1 (Mon Nov 9) | **The pipeline** | A collector that backfilled 4 quarters and is scheduled to keep going until February |
| 2 (Tue Nov 10) | **Chunks** | RAG understood, and a chunking strategy you chose on purpose |
| 3 (Wed Nov 11) | **Retrieval** | Question in, relevant chunks out, in Qdrant, with an index you can defend |
| 4 (Thu Nov 12) | **Live** | Answers with citations, deployed at a URL a stranger can open |
| 5 (Fri Nov 13) | **The number** | 30 labelled questions, four metrics, and the long-context verdict |
| 6 (Sat Nov 14) | **Make it good** | Rerank, the self-correcting retry with its rescue count, a hardened collector, and the week closed out |

---

## Day 1 (Mon Nov 9): The pipeline · ~3.5 hrs

**Mission:** get the longest dependency in the whole roadmap *running*, tonight. Not perfect. Running.

**Done when:** `data/filings/` has 4 quarters for 10–12 companies, the GitHub Action is scheduled and has fired once, and re-running the backfill adds zero duplicate files.

### Phase 1: Get one filing · ~40 min
References. No good video exists for Indian filings specifically, so these are it:
- **`bse` usage docs. Read this first:** https://bennythadikaran.github.io/BseIndiaApi/usage.html (the `announcements` section) and the category names at https://bennythadikaran.github.io/BseIndiaApi/Constants.html
- **The pagination example:** https://github.com/BennyThadikaran/BseIndiaApi/blob/main/src/examples/get_all_announcements.py. It fetches *today's* announcements for *all* companies. You'll add `scripcode`, `from_date`, `to_date` and `category`
- ~~Drishti blog~~: removed. It's a tutorial for a paid API (`drishti-sdk`, needs a key) and doesn't use `bse` at all

The call you'll make (signature from the 3.3.4 docs):
```python
bse.announcements(page_no=1, from_date=datetime, to_date=datetime,
                  scripcode="500325", category="Result")   # → {"Table": [...rows], "Table1": [{"ROWCNT": n}]}
bse.getScripCode("RELIANCE")  # → "500325"
```

⚠️ **What comes back is metadata, not text.** Each row has `NEWSID`, `HEADLINE`, `NEWS_DT`, `CATEGORYNAME`, `ATTACHMENTNAME` (a `.pdf` filename). So "get one filing" is really three steps: **row → download PDF → extract text** (`pypdf` or `pdfplumber`). The docs don't give the PDF base URL. Open any announcement on bseindia.com, click the PDF, and copy the URL pattern from the address bar. That's your first five minutes.

✅ **Decided: what counts as a "filing"** (Nov 6)

> A **filing** is one announcement PDF whose kind is `result` or `transcript`. Every other announcement is skipped, but still counted in `runs.jsonl` as `skipped_other`, so you can see what you're *not* collecting.

| Kind | Priority | Why | How to recognise it |
|---|---|---|---|
| `transcript` | **Must** | Analysts ask your eval questions ("capex guidance for FY27?") and management answers in prose, often across several turns. Also the source of natural unanswerable questions ("we don't give quarterly guidance"), and of question-and-answer pairs for the Week 12 fine-tuning set | `Company Update`. Check `SUBCATNAME` first, then fall back to a headline pattern like `transcript` |
| `result` | **Must** | Tables and numbered notes, two of your three structures | `category="Result"`. Drop headlines containing `newspaper` or `intimation` |
Rejected:
- **Results only:** Day 5's prose questions would have nothing to retrieve.
- **Every announcement:** thousands of trading-window and share-certificate notices would bury the signal.
- **Presentations** (dropped Nov 6): slides extract as broken bullets and the charts are images, so the useful content is mostly lost. They'd add noise to retrieval for little prose. Easy to add later as a third kind if you want them.

Rough size: 12 companies × 4 quarters × 2 kinds ≈ **100 documents**.

- ⚠️ **Exclude "audio recording" announcements.** They mention "earnings call" too, but their PDF is just a link to the audio
- **Tune the patterns from your own data.** Print every `Company Update` headline for 2 companies, read them, *then* write the patterns. Don't guess the wording
- **Timing:** transcripts are filed several days *after* the results. The nightly incremental run picks them up whenever they land, but make the backfill window reach a week or two past the last results date

⚠️ Some PDFs are scanned images, so `pypdf` returns an empty string. Log them as `failed: no_text` and move on. Don't OCR on Monday.

Pull one announcement for one company. Download its PDF. Print the text. That's the whole phase: find out what the data actually looks like before you design anything around it.

⚠️ **Test it from GitHub Actions on Day 1, not just from your laptop.** Your laptop is a residential IP; the Action is a datacenter IP, and exchange sites treat those differently. If BSE refuses the Action, you want that failure tonight while you can still add headers or a delay — not at 1am Tuesday when the first scheduled run comes back empty. The manual `workflow_dispatch` fire in Phase 4 is exactly this test.

### Phase 2: Backfill 4 quarters · ~1.25 hrs
- 10–12 companies, 4 quarters each
- **Be polite.** Rate-limit your requests, cache what you've fetched. You're pulling a few hundred documents once, not hammering an exchange
- Backfill = one `from_date`/`to_date` window per company covering ~13 months, paged until you've seen `ROWCNT` rows. Incremental = the same function with a 3-day window (overlap is free because you're idempotent)
- ⚠️ **Idempotent means re-running changes nothing.** Key on `NEWSID` (BSE's unique id per announcement) and skip if the file exists. Derive the quarter from `NEWS_DT` for the folder name. Results for Jul–Sep are *filed* in Oct–Nov, so decide whether "quarter" means the period reported or the filing date, and write it down. Test it by running the backfill twice and diffing the directory. If the second run writes anything, it's not idempotent, and Week 12 will quietly end up with duplicate training examples

### Phase 3: A run log · ~25 min
Keep this tonight even though the rest of the hardening moves to Saturday — you need it because **you will not be watching.**

`runs.jsonl`, one line per run: timestamp, fetched (by kind), skipped (already exists), skipped_other (not a filing kind), failed (including `no_text`), duration. Plus one command that prints the last run's line, so "did it work?" is a two-second question.

### Phase 4: Schedule it · ~1 hr
```yaml
name: collect
on:
  schedule: [{ cron: "30 19 * * *" }]   # 01:00 IST
  workflow_dispatch:
jobs:
  collect:
    runs-on: ubuntu-latest
    permissions: { contents: write }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: python -m collector.schedule --incremental
      - run: |
          git config user.name "collector"
          git config user.email "collector@users.noreply.github.com"
          git add data/ && git diff --staged --quiet || git commit -m "filings $(date -u +%F)"
          git push
```
- ⚠️ **`workflow_dispatch` is not optional.** You need to be able to fire it by hand to test it, and you will
- ⚠️ GitHub disables scheduled workflows on repos with no activity for 60 days. You'll be pushing through December so it won't bite — but know it exists, because it's exactly the kind of silent failure that surfaces in January with no time to recover
- **Fire it manually before bed. Watch it run. Confirm it committed.** The week has no second chance at this before you travel

**Moved to Nov 14:** retries with backoff, and the deliberate-failure drill (point it at a dead ticker, confirm one bad company doesn't kill the night). Worth doing — just not worth Monday.

**Before bed:** write your guess for the Day 1 scoreboard row — how many filings did you get? Then count them.

---

## Day 2 (Tue Nov 10): Chunks · ~3.5 hrs

**Mission:** first contact with RAG, and the one decision that will move your recall more than anything else this week.

**Done when:** you can explain retrieval end to end in your own words, and `chunk.py` splits a real filing in a way you chose for a reason.

### Phase 1: Watch · ~50 min
1. **What is RAG? Completely explained in 15 minutes** (Apna College): https://www.youtube.com/watch?v=Ty8gcCKuwNI
2. **RAG explained in 20 minutes, with a hands-on project**: https://www.youtube.com/watch?v=RosLeHGBLoY

Both are concept videos, which is fine for Day 2, but neither is about *chunking*, and chunking is the day's actual job. Add one:
3. **Chunking Strategies for RAG** (Padho with Pratyush · Aug 2026 · 29 min · hands-on): https://www.youtube.com/watch?v=bm_0jH5ve8U. Fixed, paragraph, recursive and markdown-aware chunking, run live on the same document. It doesn't cover tables or semantic chunking, so pair it with:
4. **Document Processing Pipeline for RAG with Docling** (Venelin Valkov · Apr 2025 · 26 min · hands-on): https://www.youtube.com/watch?v=B5XD-qpL0FU. PDF parsing with OCR, structure-aware chunking, and semantic chunking. **This is the one for keeping tables intact**, which is exactly your Day 5 fix. Watch it before you fight `pdfplumber`
- *Optional classic:* Greg Kamradt, **5 Levels of Text Splitting** (Jan 2024 · 69 min · 276 comments): https://www.youtube.com/watch?v=8OJC21T2SL4. Older and long, so skip it unless you're hooked

Write down, in your own words: what's stored, what's compared, and what the model actually sees at answer time. If you can't write that in four lines, rewatch rather than continuing.

### Phase 2: Look at your data · ~40 min
Open five filings and read them. Actually read them. You are about to make a chunking decision and the only input that matters is what these documents look like.

Three structures, three problems:
- **Tables** — a chunk that splits a table from its header is worthless. The numbers survive, the meaning doesn't
- **MD&A prose** — long, discursive, and the answer is often spread across two paragraphs
- **Numbered notes** — short, self-contained, each basically its own document

### Phase 3: Chunk · ~2 hrs
Start with recursive character splitting, 512 tokens, 50 overlap. It is the default and it will be wrong in an interesting way — that's the point, it's your baseline.
- **Keep metadata on every chunk**: ticker, quarter, date, and where in the document it came from. Citations need it and the eval needs it
- ⚠️ **If tables come out mangled, don't spend an hour fighting `pdfplumber`.** Try a vision model on the page image instead — reading the page as a picture is frequently more accurate than another parser. Timebox the parser attempt to 30 minutes, then switch

### 🔥 Challenge: place your bets · ~10 min
Fill in the guess column: recall@5 on this first attempt, and how many chunking strategies you'll end up trying. No peeking at what anyone recommends.

---

## Day 3 (Wed Nov 11): Retrieval · ~3.5 hrs

**Mission:** question in, right chunks out.

**Done when:** Qdrant holds your corpus, a question returns ranked chunks, and you have written one sentence defending your index choice.

### Phase 1: Embed and store · ~1.75 hrs
- `docker run -p 6333:6333 qdrant/qdrant`
- `bge-small-en-v1.5` via `sentence-transformers`. First call downloads ~130MB, then it's local and free
- **Qdrant hybrid search in Python, BM25 + dense vectors**: https://www.youtube.com/watch?v=t0h2-F1AHqA
- Hybrid matters here more than usual: filings are full of exact tokens — ticker symbols, "Q3FY26", section numbers — that dense vectors blur and BM25 nails
- ⚠️ **bge gotcha #1:** bge-small v1.5 expects queries (not chunks) prefixed with `"Represent this sentence for searching relevant passages: "`. Skip it and recall silently drops a few points. Check the model card
- ⚠️ **bge gotcha #2:** it truncates at **512 tokens**. If your chunks are 512 *characters* that's fine. If they're 512 tokens from a different tokenizer, the tail of some chunks is never embedded
- Consider **`fastembed`** (Qdrant's own library, ONNX, no PyTorch) instead of `sentence-transformers`. It runs bge-small *and* BM25 sparse vectors, and it matters on Day 4 (see the RAM warning)

### Phase 2: The index decision · ~30 min
⚠️ **Correction to the framing below: Qdrant only does HNSW.** IVFFlat is a pgvector/FAISS option, so there's no switch to flip in Qdrant. The real decisions in Qdrant are:
1. **HNSW vs exact (brute-force) search.** Qdrant skips the index and scans everything below `full_scan_threshold`. At a few thousand chunks you may be doing exact search without knowing it. Find out
2. **HNSW params:** `m` and `ef_construct` (build), `hnsw_ef` (query)
3. **Why Qdrant over pgvector**, where IVFFlat *would* have been the choice

So the defensible line looks like: *"At ~N chunks exact search costs X ms, so the index barely matters. I chose Qdrant for built-in hybrid, and I'd revisit HNSW params past ~100k chunks."* That's a better answer than picking HNSW blind.

Watch (~28 min):
1. **Vector Search & ANN: FAISS (HNSW & IVF)** (Mustafa Zaki · Feb 2025 · 19 min): https://www.youtube.com/watch?v=chz74Mtd1AA. A conceptual comparison of HNSW and IVF, which is exactly the trade-off you need to put into words
2. **Qdrant Essentials: HNSW Indexing** (Qdrant's own channel · Oct 2025 · 9 min · hands-on): https://www.youtube.com/watch?v=-q-pLgGDYr4. The real knobs: `m`, `ef_construct`, `hnsw_ef`
- *If you want code:* James Briggs, **HNSW Explained and Implemented with Faiss** (2021 · 35 min): https://www.youtube.com/watch?v=QvKMwLjdK-s

**Pick, and write the reason in `store.py` as a comment.**

The shape of the answer: HNSW builds slower and uses more memory but gives better recall at the same latency; IVFFlat builds fast and is cheaper but needs its probe count tuned and degrades on small collections. At a few thousand chunks, one of these is obviously right.

⚠️ Twenty minutes of reading, and disproportionately worth it. Hiring guides name this exact choice, and "HNSW, because at this corpus size recall matters more than build time" is the difference between having used a vector DB and having chosen something.

### Phase 3: Retrieve and eyeball · ~1.25 hrs
Ask ten questions by hand. Read what comes back. Are the right chunks in the top 5? You have no metrics yet — that's Day 5 — so this is pure eyeballing, and the point is to catch anything catastrophic now rather than discover it inside a metric later.

---

## Day 4 (Thu Nov 12): Live · ~3.5 hrs

**Mission:** answers with citations, and the first URL you have ever shipped.

**Done when:** a stranger can open a link, ask a question, and see the snippet the answer came from.

### Phase 1: Answer with citations · ~1.75 hrs
- Retrieved chunks → Haiku → answer, **with the chunk id it used**
- ⚠️ **Make refusal a first-class path, not an afterthought.** If the chunks don't support an answer, the correct output is "not disclosed in the filings I have." Six of your 30 eval questions test exactly this
- Thin page: question box, answer, cited snippet revealed on hover. Your frontend background makes this twenty minutes; don't spend more

### Phase 2: Deploy · ~1.75 hrs
Render or Railway, free tier, FastAPI. Qdrant goes to their free cloud tier or runs alongside.

⚠️ **RAM is the likely deploy killer.** Free tiers are around 512 MB, and `sentence-transformers` pulls in PyTorch, which alone can exceed that. Out-of-memory (OOM) crashes on boot look like mysterious restarts. Two fixes: embed queries with **`fastembed`** (ONNX, small), or use Qdrant Cloud's free cluster so the server holds only the query-embedding model. Decide this on Day 3 when you pick the embedding library, not at 10pm on Thursday.

Watch:
1. **Deploy Your Python API to Render in 5 Mins** (pixegami · Oct 2025 · 12 min · hands-on): https://www.youtube.com/watch?v=tLd5GsixfU4. A FastAPI app on Render's free tier, with code on GitHub
   - Backup: **Deploy FastAPI Apps on Render** (Programming with Kumaresan · Aug 2025 · 8 min): https://www.youtube.com/watch?v=Pv-4iYZwqUY
2. **Qdrant Vector Database** (Padho with Pratyush · Aug 2026 · 31 min · hands-on): https://www.youtube.com/watch?v=7bxSYeNSWmQ. A free Qdrant Cloud cluster, uploading embeddings, and search from Python
   - Short version: **Qdrant Cloud Overview** (Qdrant · Oct 2025 · 4 min): https://www.youtube.com/watch?v=PLTlJyrSkng. Create the cluster, get the API key, done
- Railway: no good FastAPI video exists, so **use Render**

Optional, for citations: Claude's API has built-in citation support for documents and search results. Check the Claude API docs for "citations" before hand-rolling chunk-id parsing, though hand-rolling teaches more.

⚠️ **Deploy it even though it isn't finished.** You have three repos and zero live URLs, and both hiring sources you looked at named that as a primary signal. A rough thing at a URL beats a polished thing on your laptop, and the remaining days push to the same deployment.

⚠️ First deploys always overrun. If you're two hours in and fighting it, **stop** — Nov 14 exists for this, and Day 5 is the one day this week that genuinely cannot move.

---

## Day 5 (Fri Nov 13): The number · ~3.5 hrs

**Mission:** stop guessing whether retrieval works. **This is the day the week is for.**

**Done when:** `EVAL.md` has recall@5, MRR, faithfulness and refusal rate, plus the long-context verdict.

### Phase 1: Write 30 questions · ~1.25 hrs
- **24 answerable.** For each, note which filing and roughly which section holds the answer — that's your ground truth for recall
- **6 unanswerable.** Guidance a company never gave, a segment it doesn't break out, a quarter you haven't collected. Correct behaviour is refusal
- ⚠️ **Write these yourself, from companies you follow.** Not with the model. Same rule as mini-agent and smallest-eval: a model that writes its own test questions writes ones it can answer
- Spread them across the three structures — some need a table, some need prose, some need a note

### Phase 2: Metrics · ~1 hr
- **recall@5** — is the right chunk in the top 5? Set overlap, same shape as the jd-lens precision/recall you already wrote
- **MRR** — if the right chunk is 4th, that scores 0.25. Captures what recall@5 can't: *how far down* the answer sits
- **Faithfulness** — does the answer only claim what the chunks support? An LLM judge, and you calibrated one last week. Reuse the rubric shape from `smallest-eval`
- **Refusal rate** — of the 6 unanswerable, how many did it correctly decline?
- Reference: **recall@K, precision@K, MRR, MAP, NDCG**: https://www.youtube.com/watch?v=-dIm4EyUrrM · **RAGAS for beginners**: https://www.youtube.com/watch?v=5fp6e5nhJRk

### Phase 3: Fix the chunking once · ~30 min
Now you have a number, change the thing you suspected on Day 2 — probably the tables — and re-run. Two configs, two numbers, in `EVAL.md`.

⚠️ Change **one** thing. If you change chunk size and overlap and top-k together and recall moves, you've learned nothing.

### Phase 4: The long-context baseline · ~45 min
Cheap now that the harness exists. Stuff whole filings into a long-context model, run the same 30 questions, compare accuracy, latency and ₹.
- **Why RAG beats long context in 2026** — a position to test, not accept: https://www.youtube.com/watch?v=01yspnyfUMI
- ⚠️ **Make the comparison fair:** with **prompt caching**, the stuffed documents are paid at full price once and then at a fraction for the other 29 questions. Report long-context ₹ both with and without caching. Without that, the "14× more" number is a strawman a senior interviewer will spot
- Treat the video as an opinion piece, not a tutorial. Its title argues one side. That's fine, because your numbers are the rebuttal or the confirmation
- Write the verdict even if — **especially if** — long-context wins on accuracy. It probably will, at many times the cost. Knowing when *not* to build RAG is the senior version of this skill

---

## Day 6 (Sat Nov 14): Make it good · ~6 hrs

**Mission:** turn a working RAG into one with three things most people's don't have — a reranker that's measured, a retry that's counted, and a pipeline that survives a bad night.

**Done when:** `EVAL.md` has a before/after row for reranking, the rescue count is written down, and the collector keeps going when a fetch fails.

**You travel tomorrow.** If Days 1–5 slipped, this is where the remainder lands and the items below get cut from the bottom.

### Phase 1: Rerank · ~1.5 hrs
Retrieve top 20 with the bi-encoder, rerank with a local cross-encoder (`ms-marco-MiniLM-L-6-v2`), keep 5.

The bi-encoder embedded your chunks before it ever saw the question; the cross-encoder reads question and chunk *together*, which is why it's more accurate and why you can't use it on the whole corpus. Retrieve wide and cheap, rerank narrow and expensive.

Watch:
1. **ReRanking in RAG: Bi-Encoders vs Cross-Encoders & Code** (Yash Patil · Jul 2026 · 32 min · hands-on): https://www.youtube.com/watch?v=YB6Z3X5dunI. Theory first, code from **22:17**
2. **RAG Reranking: Bi-Encoder vs Cross-Encoder, with benchmarking code** (Abid Saudagar · Aug 2026 · 12 min): https://www.youtube.com/watch?v=tA85v3aGBIU. Measures recall *and* latency before and after, which is the same before/after row your `EVAL.md` needs
- *Closest to your exact model:* **Rerank VectorDB Results with a Cross-Encoder** (Neural with Mohit · Oct 2025 · 30 min): https://www.youtube.com/watch?v=uVwrFDhvAE4. Uses `ms-marco-MiniLM` on ChromaDB

The API you'll call is `sentence_transformers.CrossEncoder`.

⚠️ **Re-run the eval and record recall@5 and MRR before and after.** The entire value is the delta. Reranking that you didn't measure is indistinguishable from reranking that did nothing.

### Phase 2: The self-correcting retry · ~1.5 hrs
Grade the retrieved chunks *before* answering. Weak? Rewrite the query and retry once. Then answer or refuse.
- Self-corrective RAG with LangGraph: https://www.youtube.com/watch?v=uZoz3T3Z6-w
- Corrective RAG (CRAG) tutorial: https://www.youtube.com/watch?v=cAdu8mO01Bo
- Query-rewriting techniques: https://www.youtube.com/watch?v=LM7oOzD2WXc
- ⚠️ The first two videos build it in **LangGraph**. Watch them for the *shape* (grade → rewrite → retry → answer), then build it by hand with plain `if`s, the same as mini-agent had no framework. It's about 30 lines. Bringing in LangGraph for one branch and one retry is the wrong trade, and "I didn't need the framework" is a better interview line
- **The CRAG paper, explained:** CampusX, **Advanced RAG: Corrective RAG (CRAG)** (Feb 2026 · 76k views · 183 comments): https://www.youtube.com/watch?v=41XDn81nR5c. The video is 75 min, but **watch only 15:53–23:00**: the correct/incorrect/ambiguous cases and the retrieval evaluator. Your version is a simplified CRAG without the web-search fallback

⚠️ **Count how often the rewrite actually rescues an answer, out of 30.** That number is the whole point. If it's 1 in 30, write "1 in 30" — a measured "this barely helped" is a stronger answer than an unmeasured feature, and it's what separates you from naive chunk-and-retrieve.

⚠️ Cap it at one retry. A grader that can trigger another grader is a loop, and you learned that in Week 2.

### Phase 3: Harden the collector · ~45 min
- **Retries with backoff** on network failure
- **The failure drill:** point the fetcher at a ticker that doesn't exist, and at a URL that 404s. Does the run log record the failure and keep going, or does the whole night die on one bad company? Fix whichever it is

A pipeline that stops on the first error is a script. This is the 45 minutes that makes the word "pipeline" honest on your CV.

### Phase 4: Close out · ~1.5 hrs
- **`EVAL.md`** — the metrics table across every config (baseline chunking, fixed chunking, + rerank), the chunking decision and why, the index choice and why, the rescue count, the long-context verdict
- **README** — lead with the metrics table and the live URL, not with "this is a RAG project." State your chunk size and top-k, and defend both
- **Scoreboard** — fill the Actual column. See how wrong you were

### ⚠️ Before you fly

**Check the collector has fired every night since Monday.** Everything else here can slip to Nov 23; this cannot. Every night it doesn't run is filings that won't exist in January, and Week 12 has no fine-tuning dataset without them.

---

## Optional build video

Your standing rule: one optional project video a week, built if there's time, skipped without guilt. **Pick one before Monday and write it here.**

→ *(fill this in)*

---

## The habits

- 5 applications + 2 outreach — **this week they go out.** After Day 5 there is no RAG left to wait for
- One post or log
- `ccusage` once, and check the collector's file count while you're there
- **Udemy:** the Week 3 catch-up — Week 1 day 5, then Week 2 day 1. Background watching across the whole week, about an hour a day, not a slot of its own
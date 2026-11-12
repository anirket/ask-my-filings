# ask-my-filings: Plan

## What we're building

**Two things, and the first one is three hours of plumbing that three later weeks depend on.**

**1. `collector` — one re-runnable command that pulls Indian company filings for any date window.** No LLM, no cleverness. Pull quarterly results and earnings-call transcripts for 11 large-caps, store the raw text with ticker, quarter and date, and re-run it whenever you want newer filings (Q3 in January, before Week 12). The collector code stays local (gitignored); only the filings are committed.

**2. `ask-my-filings` — RAG over that corpus, with its retrieval actually measured.** Ask "what did Reliance say about capex guidance last quarter?" and get an answer with the exact cited snippet, or an honest refusal when the filing never said.

```
                 ┌──────────────────────────────────────────┐
  BSE      ──►   │ collector (local, run by hand)           │
                 │  --from / --to any window, ≤365d/call    │
                 │  idempotent · run log · retries          │
                 └────────────────┬─────────────────────────┘
                                  ▼  data/filings/*.txt
                 ┌──────────────────────────────────────────┐
  question ──►   │ chunk ─► embed ─► Qdrant ─► retrieve      │
                 │   ─► answer with citations, or refuse     │
                 │   (rerank + retry: moved to Week 6)       │
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

- **`ask-my-filings`**: public repo, README leading with the metrics table
- **A corpus you can top up with one command** (re-run in January for Q3) when Week 12 needs it for the fine-tuning dataset
- **`EVAL.md`**: the four metrics, the chunking decision and why, and the RAG-vs-long-context verdict

**Done when:**

- [ ] The backfill is re-runnable over any date window, and running it twice changes nothing
- [ ] ~~Live URL~~ — dropped Nov 13; deployment is Week 9's subject
- [ ] recall@5, MRR, faithfulness and refusal rate written down for your final config
- [ ] The RAG-vs-long-context verdict, with ₹ and latency alongside accuracy
- [ ] You can defend your chunk size, your top-k and your index choice with reference to how filings are actually structured

**6 days, Nov 9 → Nov 14.** Nov 9–13 are weekday evenings at ~3.5 hrs. **Friday carries the whole remaining build; Saturday is Udemy.** Deploy is dropped — Week 9 covers it.

> ⚠️ **The plan grew about 30% after it was written** — the filing-kind classification, the PDF download-and-extract step, the bge gotchas. Since there's no backup day, **the order of sacrifice is fixed in advance: deploy slips before the eval does, and the eval never slips.**

---

## Scoreboard (fill in as you go)

| | Your guess | Actual |
|---|---|---|
| Filings in the backfill after Day 1 | | **91** |
| recall@5 on your **first** chunking attempt | | |
| recall@5 on your final config | | |
| MRR, final | | |
| Chunking strategies it took | | |
| Does long-context beat RAG on accuracy? (y/n) | | |
| ₹ per question — RAG vs long-context | | |
| Unanswerable questions correctly refused (out of 6) | | |
| ₹ spent on the whole week | | |

*Rerank delta and retry rescue count moved to Week 6 along with the work.*

Guess before you measure. Being wrong is the interesting part, and "I expected 0.9 and got 0.6" is a better story than a number with no prediction attached.

---

## Decisions made up front

| Choice | Pick | Why |
|---|---|---|
| **Where the collector runs** | Locally, by hand. No scheduler, nothing automated committed *(Nov 8)* | You're not putting code you can't defend into a public repo an interviewer will open. The backfill takes a date window, so pulling new filings is one command — including a Q3 re-run in January before Week 12 |
| **Where filings are stored** | Committed as `.txt` under `data/filings/TICKER/FY27-Q2/<kind>-<NEWSID>.txt` + a `.json` sidecar. Quarter = period reported in Indian FY terms (filing date − 45 days) | A quarter has several filings (result, transcript, sometimes a revised result), so the key is BSE's `NEWSID`, not the quarter |
| **Source** | `bse` package only, pinned `bse==3.3.4`. **No NSE** | `announcements` paginates, so one code path handles any window. ⚠️ BSE rejects ranges over 365 days (400 Bad Request), so the collector walks long ranges in 90-day windows. NSE's RSS can't backfill, and your large-caps are dual-listed anyway |
| **Vector DB** | Qdrant | Hybrid search built in, so BM25 + dense is a config change rather than a project |
| **Embeddings** | Local, `fastembed` + `BAAI/bge-small-en-v1.5` | Free, no second API key, ONNX rather than PyTorch — which is what saves you on Day 4's RAM ceiling |
| **Answering model** | `claude-haiku-5-5` | Same as every other week. Cost comparisons stay comparable |
| **Index** | Qdrant gives you HNSW — no choice to make. Day 3 is about knowing *why*, and whether you're even hitting the index | Hiring guides name "HNSW vs IVFFlat", but that's a pgvector/FAISS question. Yours is: below `full_scan_threshold` Qdrant does exact search, so at a few thousand chunks the index may be doing nothing. Find out, then say so |
| **Deploy** | **Dropped** *(Nov 13)* | Week 9 is the deployment week — Docker, Cloud Run, a load test. Nothing ships to a URL before then |
| **Reranker + self-correcting retry** | **Moved to Week 6 Day 1** *(Nov 12)* | Both need a measured before/after to mean anything. Week 6 reopens this codebase with Friday's numbers already in `EVAL.md` as the baseline |

```
ask-my-filings/
  collector/
    classifier.py       # row → result | transcript | None            (gitignored)
    fetch.py            # --from/--to → PDF → text, idempotent        (gitignored)
  data/filings/TICKER/FY27-Q2/<kind>-<NEWSID>.txt   (+ .json sidecar)  ← committed
  rag/
    chunk.py            # the decision that matters most
    embed.py            # bge-small via fastembed
    store.py            # Qdrant: index finding lives here as a comment
    retrieve.py         # hybrid search → top-k
    answer.py           # cite or refuse
  evals/
    questions.yaml      # 30 questions: 24 answerable, 6 unanswerable
    metrics.py          # recall@k, MRR, faithfulness
    longcontext.py      # the baseline that might beat you
  app.py                # FastAPI + a thin page, hover reveals the snippet
  EVAL.md  README.md  .env.example  requirements.txt
```

---

## Before Day 1 · ~20 min *(Sunday Nov 8)*

- `pip install bse==3.3.4` and confirm it imports
- ⚠️ **Pin it — `bse==3.3.4`, not `-U`.** Audited clean on Nov 6: 1,733 lines, no `eval`/`exec`/`subprocess`/`base64`, stdlib + `requests` + `mthrottle` only, sole network destination `api.bseindia.com`. But it's a single-maintainer package with ~80 stars, which is exactly the profile where a compromised account ships a bad release. Pin `mthrottle` too. It is **GPL-3.0**, so say so in your README
- **`.env` in `.gitignore` before the first commit.** The repo is public
- Docker running, so `docker run qdrant/qdrant` works on Day 3 without a detour
- Pick your companies — ones you actually follow, because you'll write eval questions about them from memory on Day 5
- ⚠️ **Find the PDF URL pattern now** (~15 min, no code). `bse` returns metadata, not text, and the URL isn't documented. If you can't construct it there's no corpus and Day 2 doesn't happen

| Day | Name | You'll walk away with |
|---|---|---|
| 1 (Mon Nov 9) | **The pipeline** | A re-runnable collector that backfilled 4 quarters for 11 companies |
| 2 (Tue Nov 10) | **Chunks** | RAG understood, and a chunking strategy you chose on purpose |
| 3 (Wed Nov 11) | **Retrieval** | Question in, relevant chunks out, in Qdrant, with an index you can defend |
| 4 (Thu Nov 12) | **Answers** | Answers with citations. ⚠️ Slipped to Friday; deploy dropped |
| 5 (Fri Nov 13) | **The number** | 30 labelled questions, four metrics, and the long-context verdict |
| 6 (Sat Nov 14) | **Udemy** | The Week 3 catch-up. No project work — Friday carries the build |

---

## Day 1 (Mon Nov 9): The pipeline · ~3.5 hrs ✅

**Mission:** get the longest dependency in the whole roadmap *running*. Not perfect. Running.

**Done when:** `data/filings/` has 4 quarters for 10–12 companies, the backfill takes a date window, and re-running it adds zero duplicate files.

### Phase 1: Get one filing · ~50 min

References — no good video exists for Indian filings specifically, so these are it:

- **`bse` usage docs, read first:** https://bennythadikaran.github.io/BseIndiaApi/usage.html (the `announcements` section) and category names at https://bennythadikaran.github.io/BseIndiaApi/Constants.html
- **The pagination example:** https://github.com/BennyThadikaran/BseIndiaApi/blob/main/src/examples/get_all_announcements.py — fetches today's announcements for all companies. You'll add `scripcode`, `from_date`, `to_date`, `category`
- ~~Drishti blog~~: removed. It's a tutorial for a paid API (`drishti-sdk`) and doesn't use `bse` at all

```python
bse.announcements(page_no=1, from_date=datetime, to_date=datetime,
                  scripcode="500325", category="Result")
# → {"Table": [...rows], "Table1": [{"ROWCNT": n}]}

bse.getScripCode("RELIANCE")  # → "500325"
```

⚠️ **What comes back is metadata, not text.** Each row has `NEWSID`, `HEADLINE`, `NEWS_DT`, `CATEGORYNAME`, `ATTACHMENTNAME` (a `.pdf` filename). So "get one filing" is three steps: **row → download PDF → extract text**.

✅ **PDF URL found:** `https://www.bseindia.com/xml-data/corpfiling/AttachLive/<ATTACHMENTNAME>` (older ones may move to `AttachHis/`). `NSURL` is the company's stock page, not the PDF. **BSE returns 403 to the python-requests User-Agent**, so download through `bse.session`, and check the bytes start with `%PDF`.

#### ✅ Decided: what counts as a "filing" *(Nov 6)*

> A **filing** is one announcement PDF whose kind is `result` or `transcript`. Everything else is skipped but counted in `runs.jsonl` as `skipped_other`, so you can see what you're *not* collecting.

| Kind | Why | How to recognise it |
|---|---|---|
| `transcript` | Analysts ask your eval questions ("capex guidance for FY27?") and management answers in prose. Also the source of natural unanswerable questions, and of Q&A pairs for the Week 12 fine-tuning set | `Company Update`. Check `SUBCATNAME` first, then fall back to a headline pattern like `transcript` |
| `result` | Tables and numbered notes, two of your three structures | `CATEGORYNAME == "Result"`, or `SUBCATNAME == "Outcome of Board Meeting"` confirmed by the PDF text mentioning "financial results" (HDFC Bank, LIC, L&T and Kotak file results only this way; LIC also uses it for a bonus issue, which the text check rejects) |

**Rejected:**

- **Results only** — Day 5's prose questions would have nothing to retrieve
- **Every announcement** — thousands of trading-window and share-certificate notices would bury the signal
- **Presentations** *(dropped Nov 6)* — slides extract as broken bullets and the charts are images. Easy to add later as a third kind

Rough size: 12 companies × 4 quarters × 2 kinds ≈ 100 documents.

**Actual (Nov 8): 91 filings**, after removing cover letters, Kotak, L&T and duplicates.

⚠️ **Cover-letter-only filings** (a 1–10k-char letter saying "accessible at the link below") are rejected as `cover_letter_only`: transcripts under 10k chars, results under 15k. Kotak and L&T were dropped for this reason; HDFC and LIC lose some results the same way. Say so in the README, and use it for unanswerable questions on Day 5.

✅ **Duplicates removed (Nov 8).** BSE often files the same PDF twice under two `NEWSID`s (as `Result` and as `Outcome of Board Meeting`). **35 of 126 files were byte-identical.** The collector now hashes the extracted text (sha256, stored in the sidecar) and skips a filing whose text already exists, keeping the `Result`-category copy first, then the earliest. Near-duplicates (same statements, different cover page) can still exist — check on Day 2 if the same table crowds your top-5.

- ⚠️ **Exclude "audio recording" announcements.** They mention "earnings call" too, but their PDF is just a link to the audio
- **Tune the patterns from your own data.** Print every `Company Update` headline for 2 companies, read them, *then* write the patterns
- **Timing:** transcripts are filed several days after results. Re-run a recent window to pick them up whenever they land
- ⚠️ Some PDFs are scanned images, so `pypdf` returns an empty string. Log them as `failed: no_text` and move on. Don't OCR on Monday

### Phase 2: Backfill 4 quarters · ~1.25 hrs

- **11 companies** *(Nov 8 picks)*: RELIANCE, BHARTIARTL, JPL, HDFCBANK, ICICIBANK, SBIN, TCS, BAJFINANCE, LICI, INFY, NSE. KOTAKBANK and LT dropped — their BSE transcripts are cover letters linking to their own sites. JPL and NSE are recent listings, so expect fewer quarters
- **Be polite.** Rate-limit, cache what you've fetched. You're pulling a few hundred documents once, not hammering an exchange
- Backfill = one window per company covering ~13 months (default 400 days), **split into 90-day calls because BSE caps a call at 365 days**, each paged until you've seen `ROWCNT` rows
- ⚠️ **Idempotent means re-running changes nothing.** Key on `NEWSID` and skip if the file exists. Derive the quarter from `NEWS_DT`. Results for Jul–Sep are *filed* in Oct–Nov, so decide whether "quarter" means the period reported or the filing date, and write it down. Test by running the backfill twice and diffing the directory

### Phase 3: A run log · ~25 min

Keep this — runs are by hand, but the January re-run is one you'll start and walk away from.

`runs.jsonl`, one line per run: timestamp, fetched (by kind), skipped, `skipped_other`, failed (including `no_text`), duration, and the from/to window. Plus `python -m collector.fetch --last` to print the last run's line, so "did it work?" is a two-second question.

### Phase 4: Make it re-runnable · ~40 min

**No scheduler, no GitHub Action** *(Nov 8)*.

```
python -m collector.fetch --from 2026-01-01 --to 2026-03-31
```

Same function either way; the window is just an argument. Because you key on `NEWSID` and skip existing files, overlapping windows are free.

**What this buys you:** transcripts that land late · **Q3 FY26 in January**, the biggest batch of new filings inside your roadmap, right before Week 12 · nothing in the repo you didn't write.

⚠️ **Put the January re-run in the README.** The failure mode isn't technical, it's forgetting.

---

## Day 2 (Tue Nov 10): Chunks · ~3.5 hrs ✅

**Mission:** first contact with RAG, and the one decision that will move your recall more than anything else this week.

**Done when:** you can explain retrieval end to end in your own words, and `chunk.py` splits a real filing in a way you chose for a reason.

### Phase 1: Watch · ~55 min

⚠️ **Pick one of 1 and 2, not both.** They cover the same ground.

1. **What is RAG? Completely explained in 15 minutes** (Apna College): https://www.youtube.com/watch?v=Ty8gcCKuwNI
2. **RAG explained in 20 minutes, with a hands-on project**: https://www.youtube.com/watch?v=RosLeHGBLoY
3. **Chunking Strategies for RAG** (Padho with Pratyush · Aug 2026 · 29 min · hands-on): https://www.youtube.com/watch?v=bm_0jH5ve8U — **the one that's actually about today's job**
4. **Document Processing Pipeline for RAG with Docling** (Venelin Valkov · Apr 2025 · 26 min): https://www.youtube.com/watch?v=B5XD-qpL0FU — **save for Day 5 Phase 3**, when a recall number tells you tables are the problem

Write down, in your own words: what's stored, what's compared, and what the model actually sees at answer time. If you can't write that in four lines, rewatch rather than continuing.

### Phase 2: Look at your data · ~40 min

Open five filings and read them. Three structures, three problems:

- **Tables** — a chunk that splits a table from its header is worthless. The numbers survive, the meaning doesn't
- **MD&A prose** — long, discursive, the answer often spread across two paragraphs
- **Numbered notes** — short, self-contained, each basically its own document

### Phase 3: Chunk · ~2 hrs

Recursive character splitting, ~500 tokens, 50 overlap. The boring baseline, deliberately.

- **Keep metadata on every chunk**: ticker, quarter, kind, and where in the document it came from
- ✅ **Measure length with bge's own tokenizer**, not characters — bge truncates at 512 of *its* tokens
- ⚠️ **Keep `chunk_size` under 512.** bge wraps input in `[CLS] … [SEP]`, so a 512-token chunk becomes 514 and gets truncated. Your 50-token overlap means nothing is actually lost, but 500 is the honest number to put in a README
- ⚠️ **If tables come out mangled, don't fight `pdfplumber` for an hour.** Try a vision model on the page image. Timebox the parser attempt to 30 minutes

---

## Day 3 (Wed Nov 11): Retrieval · ~3.5 hrs

**Mission:** question in, right chunks out.

**Done when:** Qdrant holds your corpus, a question returns ranked chunks, and you've written one sentence defending your index choice.

### Phase 1: Embed and store · ~1.75 hrs

- `docker run -p 6333:6333 qdrant/qdrant`
- `bge-small-en-v1.5` via **`fastembed`** (ONNX, no PyTorch — this is what saves Day 4's deploy)
- **Qdrant hybrid search, BM25 + dense**: https://www.youtube.com/watch?v=t0h2-F1AHqA — *skip if you've already built the toy*
- Hybrid matters here more than usual: filings are full of exact tokens — ticker symbols, `Q3FY26`, section numbers — that dense vectors blur and BM25 nails
- ✅ **`Modifier.IDF` is required** on the sparse config or BM25 scores are meaningless
- ⚠️ **bge query prefix — tested Nov 12: `query_embed` does NOT add it.** Prepend it yourself:
  ```python
  PREFIX = "Represent this sentence for searching relevant passages: "
  dense_query = next(dense_model.query_embed(PREFIX + question))
  ```
  **Dense query only.** Chunks never get it. **The BM25 query never gets it either** — BM25 is literal term matching, so the prefix would make every document containing "relevant" start scoring. Put the prefix inside the function that embeds a question, not at the call sites
- ⚠️ **Measure whether the prefix helps.** On Day 5 you'll have 30 labelled questions; running with and without it is one line and gives you a number instead of a belief. Either result is an `EVAL.md` row

### Phase 2: The index decision · ~30 min

**Qdrant only does HNSW.** IVFFlat is a pgvector/FAISS option, so there's no switch to flip. The real questions are:

1. **HNSW vs exact search.** Qdrant skips the index below `full_scan_threshold`. At a few thousand chunks you may be doing exact search without knowing. **Find out**
2. **HNSW params:** `m`, `ef_construct` (build), `hnsw_ef` (query)
3. **Why Qdrant over pgvector**, where IVFFlat *would* have been the choice

The defensible line: *"At ~N chunks exact search costs X ms, so the index barely matters. I chose Qdrant for built-in hybrid, and I'd revisit HNSW params past ~100k chunks."* Better than picking HNSW blind.

Watch: **Qdrant Essentials: HNSW Indexing** (Qdrant · Oct 2025 · 9 min · hands-on): https://www.youtube.com/watch?v=-q-pLgGDYr4 — the real knobs.

*Defer unless you want the interview background:* **Vector Search & ANN: FAISS (HNSW & IVF)** (19 min): https://www.youtube.com/watch?v=chz74Mtd1AA

**Write the reason in `store.py` as a comment.**

### Phase 3: Retrieve and eyeball · ~1.25 hrs

Ask ten questions by hand. Read what comes back. Are the right chunks in the top 5? No metrics yet — that's Day 5 — so this is pure eyeballing, to catch anything catastrophic now rather than discover it inside a metric later.

---

## Day 4 (Thu Nov 12): Live · ~3.5 hrs

**Mission:** answers with citations, and the first URL you have ever shipped.

**Done when:** a stranger can open a link, ask a question, and see the snippet the answer came from.

### Phase 1: Answer with citations · ~1.75 hrs

⚠️ **This is not the optional half.** Friday's faithfulness and refusal metrics both score *answers* — without this, only 2 of your 4 metrics exist. If the evening runs short, drop deploy, not this.

- Retrieved chunks → Haiku → answer, **with the chunk id it used**
- ⚠️ **Make refusal a first-class path.** If the chunks don't support an answer, the correct output is "not disclosed in the filings I have." Six of your 30 questions test exactly this
- Thin page: question box, answer, cited snippet on hover. Twenty minutes for you; don't spend more

### ~~Phase 2: Deploy~~ — dropped *(Nov 13)*

Not deferred, dropped. **Deployment is Week 9's subject** — Docker, Cloud Run, a load test — so the skill isn't skipped, just not practised here. The consequence to accept knowingly: no live URL for any project until late December.

⚠️ **Still worth 10 minutes: fix the import chain.** `chunk.py` loads the bge tokenizer at import, `store.py` imports `chunk_all`, and `retrieve.py` imports `client` from `store` — so anything that imports `retrieve` drags `transformers` and the whole chunking stack into memory. Move `client` into its own `rag/qdrant.py`. That's not a deploy concern, it's why a one-question script takes seconds to start.

---

## Day 5 (Fri Nov 13): The number — and everything else · the whole evening

**Mission:** stop guessing whether retrieval works. **This is the day the week is for.**

**Done when:** `EVAL.md` has recall@5, MRR, faithfulness and refusal rate, plus the long-context verdict.

> **Friday is now the whole project** *(Nov 13)*: Day 4 Phase 1 and Day 5 together, deploy cut, Saturday reserved for Udemy. That is ~5.25 hours against a work evening, so **you will probably not finish — and that's fine if you run it in the right order.**
>
> **Write `EVAL.md` as you go, not at the end.** Every number goes in the moment you have it. A half-finished `EVAL.md` with three real metrics is a shipped week; a terminal full of numbers at midnight is not.

### The order, and why

**Do the two retrieval-only metrics *before* building the answer path.** recall@5 and MRR need nothing you don't already have — retrieval works as of tonight. Faithfulness and refusal need answers. So bank the headline numbers first, while you're fresh and before anything new can break.

| # | Task | ~ | Needs |
|---|---|---|---|
| 1 | Write the 30 questions | 1.25h | nothing — do it even if tired |
| 2 | **recall@5 + MRR** | 40m | retrieval only ✅ already works |
| 3 | Day 4 Phase 1 — answer with citations | 1.75h | — |
| 4 | Faithfulness + refusal rate | 30m | step 3 |
| 5 | Long-context baseline | 45m | step 1 |
| 6 | Chunking fix + re-run | 30m | step 2 |
| 7 | README | 30m | — |

Stopping after step 2 still gives you a measured retrieval system. Stopping after step 4 gives you the full four-metric table. Steps 5–7 are the polish.

### Phase 1: Write 30 questions · ~1.25 hrs

- **24 answerable.** For each, note which filing and roughly which section holds the answer — that's your recall ground truth
- **6 unanswerable.** Guidance a company never gave, a segment it doesn't break out, a quarter you don't hold. NSE has one document and no transcript, so it's a legitimate source of these
- ⚠️ **Write these yourself.** Not with the model. A model that writes its own test questions writes ones it can answer
- Spread them across the three structures. **Draw table questions from RELIANCE, TCS, SBIN, INFY, BAJFINANCE, ICICIBANK** — they have full five-quarter coverage. HDFCBANK (6 transcripts, 2 results) and LICI are prose-only in practice

### Phase 2: Metrics · ~1 hr

- **recall@5** — is the right chunk in the top 5? Set overlap, same shape as the jd-lens precision/recall
- **MRR** — if the right chunk is 4th, that scores 0.25. Captures what recall@5 can't: *how far down* the answer sits
- **Faithfulness** — does the answer only claim what the chunks support? An LLM judge; reuse the rubric shape from `smallest-eval`
- **Refusal rate** — of the 6 unanswerable, how many did it correctly decline?

Reference: **recall@K, precision@K, MRR, MAP, NDCG**: https://www.youtube.com/watch?v=-dIm4EyUrrM · **RAGAS for beginners**: https://www.youtube.com/watch?v=5fp6e5nhJRk

### Phase 3: Fix the chunking once · ~30 min

Now you have a number, change the thing you suspected on Day 2 — probably the tables — and re-run. Two configs, two numbers, in `EVAL.md`.

⚠️ **Change one thing.** If you change chunk size and overlap and top-k together and recall moves, you've learned nothing.

### Phase 4: The long-context baseline · ~45 min

Cheap now the harness exists. Stuff whole filings into a long-context model, run the same 30 questions, compare accuracy, latency and ₹.

- **Why RAG beats long context in 2026** — a position to test, not accept: https://www.youtube.com/watch?v=01yspnyfUMI
- ⚠️ **Make the comparison fair:** with **prompt caching**, the stuffed documents are paid at full price once and a fraction for the other 29. Report long-context ₹ both with and without caching. Otherwise "14× more" is a strawman a senior interviewer will spot
- Write the verdict even if — **especially if** — long-context wins on accuracy. Knowing when *not* to build RAG is the senior version of this skill

---

## Day 6 (Sat Nov 14): Udemy catch-up

**No project work.** Udemy Week 1 day 5, then Week 2 day 1 if the day allows — the catch-up that's been sliding since Week 3.

Everything else landed on Friday or moved out:

| Was | Now |
|---|---|
| Deploy | **Dropped** — Week 9 is the deployment week |
| Rerank + self-correcting retry | **Week 6 Day 1 (Nov 24)**, ~3 hrs, with its own resources |
| Collector hardening *(retries, failure drill, ~45 min)* | Unscheduled — low-stakes now that nothing runs unattended |
| `EVAL.md`, README, scoreboard | **Friday**, written as the numbers arrive |

⚠️ **If Friday fell short, Saturday is the backstop for `EVAL.md` — not for Udemy.** Numbers that exist only in your terminal are not a shipped project. Udemy has slipped a week before and can slip again; the week's only output cannot.

### Before you fly

Nothing runs while you're away, by design — so there's nothing to check. Just make sure the README says how to re-run the backfill over a window, with the January Q3 pull called out. Future-you in two months is the one who needs that sentence.

### On the trip (Nov 15–17)

- The rest of the Udemy catch-up — passive video on a phone is exactly what travel time is for
- **5 applications + 2 outreach.** They were meant to go out this week and didn't. A hotel evening with nothing to build is the right slot
- Plan Week 5 on the 17th

### Before you fly

Nothing runs while you're away, by design — so there's nothing to check. Just make sure the README says how to re-run the backfill over a window, with the January Q3 pull called out. Future-you in two months is the one who needs that sentence.

---

## Optional build video

One optional project video a week, built if there's time, skipped without guilt.

→ *(fill this in)*

*Deferred: vectorless RAG / PageIndex tree navigation. Parked for Week 6, once there's a measured vector baseline to compare it against.*

---

## The habits

- **5 applications + 2 outreach** — this week they go out. After Day 5 there is no RAG left to wait for
- One post or log
- `ccusage` once
- **Udemy:** the Week 3 catch-up — Week 1 day 5, then Week 2 day 1. Background watching, about an hour a day
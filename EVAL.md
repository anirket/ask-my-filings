# EVAL

Numbers are written here as they arrive. Every row names the config it was measured on.

## Retrieval: baseline (Nov 13, 2026)

**Config:** chunk_size 500 / overlap 30 (bge-small tokens) · 6,439 chunks · bge-small-en-v1.5 dense + BM25 sparse · hybrid RRF (k=2) · query prefix on (dense only) · prefetch 30 per search · top-5 · ties broken by chunk_id.
**Set:** 24 answerable questions (`evals/questions.yaml`). A hit = a top-5 chunk with the expected ticker, the expected quarter, and the expected string.
**Run:** `PROMPTFOO_PYTHON=.venv-312/bin/python npx promptfoo eval --no-cache -o output/eval.json` (one config scores retrieval and answers together)

| Metric | Value |
|---|---|
| recall@5 | **14/24 = 0.58** |
| MRR | **0.42** (sum of reciprocal ranks 10.03 / 24 questions) |

**How MRR is calculated:** for each answerable question take 1 / (rank of the first correct chunk), 0 if it is not in the top 5; then average over the 24 questions.

| Rank of correct chunk | Questions | 1/rank | Contribution |
|---|---|---|---|
| 1 | 8 | 1.000 | 8.000 |
| 2 | 2 | 0.500 | 1.000 |
| 3 | 1 | 0.333 | 0.333 |
| 4 | 2 | 0.250 | 0.500 |
| 5 | 1 | 0.200 | 0.200 |
| not in top 5 | 10 | 0 | 0 |
| **Total** | **24** | | **10.033** |


## Findings so far

- **RRF scores tie, and Qdrant orders ties randomly.** The same query gave 5 different orderings in 6 runs, which would have made MRR change between identical runs. Fixed: fetch `k+10`, sort by `(-score, chunk_id)`, cut to `k`.
- **Table chunks lose their column headers** (e.g. BAJFINANCE FY27-Q2 chunks `…-6` and `…-28`): ~10% of result chunks open with numeric rows and no header.
- **`pypdf` damages numbers**: stray spaces inside figures (`17, 184.42`) and dropped decimal points (`958 09`); "Q2" is extracted as "02".
- **`start_index` is -1 on 2,093 of 6,439 chunks** (33%), so character positions for citations are unreliable. Cause: LangChain's `add_start_index` searches for each chunk from `previous_start + len(previous_chunk) - chunk_overlap`, mixing characters with our token-based `chunk_overlap` (30 tokens is ~100+ characters), so the search window starts after the real chunk start. Not data corruption: in a 1,737-chunk sample, all 614 chunks with -1 appear verbatim in the document. Fix if positions are ever needed: compute them in `chunk_filing` with `doc.find(chunk, previous_start + 1)`.
- **Boilerplate/header chunks** (addresses, "Final Transcript", page footers) crowd the top 5.
- **Retrieval always returns something**, even for unanswerable questions, so refusal has to come from the answer step.

## Retrieval failures: two different problems (10 of 24 misses)

- **Right filing, wrong chunk** (the number's chunk is not in the top 5): q02, q03, q21, q22, q24. A chunk-level problem.
- **Wrong company or wrong quarter** in the top 5: q07, q16, q17, q19, q20. A routing problem.


## Answers: baseline (Nov 13, 2026)

**Config:** same retrieval as above (top-5) · answerer `claude-haiku-5-5` with structured output (`answerable`, `answer`, `cited` chunk ids), which also returns the 5 chunks it saw · judge `claude-haiku-5-5`.
**Run:** the same single command as above: 30 questions, ~65 s. Retrieval metrics are read from the returned chunks, so they are identical to the retrieval-only run (14/24, 10.03/24).

| Metric | Value |
|---|---|
| **Refusal rate** (unanswerable questions correctly refused) | **6/6** |
| **Faithfulness** (answered questions where every claim is supported by the chunks) | **14/16 = 0.88** |
| Answered at all (of 24 answerable) | 16/24 |
| False refusals (answerable, but the system said "not disclosed") | 8/24 |
| Citations valid (every cited chunk_id was among the 5 retrieved) | 16/16 of the answered ones |
| Answer contains the expected string | 12/24 (strict substring; see caveat) |

**False refusals follow retrieval misses.** The 10 retrieval misses (above) are the ceiling: when the right chunk is not in the top 5 the model says "not disclosed" instead of guessing. It refused all 6 unanswerable questions and never invented a number for one.

**Caveats**
- *Run-to-run variation:* the answer model is not pinned to temperature 0. An earlier identical run gave 17 answered / 13 expected-string matches / 13 of 17 faithful, this one 16 / 12 / 14 of 16. Retrieval is deterministic; answers are not, so treat answer metrics as ±1-2 questions.
- *Faithfulness judge:* an LLM rubric (PASS if every claim in `answer` is supported by the chunk text; a refusal passes). It replaced promptfoo's built-in `context-faithfulness`, which scores a refusal as a parse failure. In the earlier run 2 of 4 failures were judge errors ("No output", "Could not extract JSON"); this run had none. The two real failures: q06 converted units ("INR 12,131 million, about crore") and q23 added detail beyond the chunk.
- *Expected-string check is too strict:* correct answers get marked wrong by wording (`Rs 264` vs `Rs.264`, `INR 12 per equity share` vs `Equity Share`), so true correctness is nearer 15-16/24. A wrong-quarter answer (HDFC deposits from FY26-Q4) does happen.
- *Cost:* promptfoo does not report the Python provider's spend. The judge alone used ~148k tokens per run; answer-generation tokens are not tracked yet.

## Experiment 1: context header on every chunk (Nov 13, 2026)

**Change (one thing):** the text that is *embedded* (dense and BM25) now starts with a line built from the chunk's metadata, e.g. `Tata Consultancy Services (TCS) | FY27-Q2 | earnings call transcript`. The stored chunk text, chunk boundaries (500/30) and everything else are unchanged. New collection `FILINGS_CTX`; the baseline is `FILINGS`.
**Why:** all 10 baseline misses had an answer-bearing chunk, but none of those chunks said which company or quarter they came from (the identity was only in metadata, which is not embedded), so a question naming "TCS" or "FY27" had nothing to match.
**Cost of the change:** the header (<= 30 tokens) pushes 2,187 chunks over bge's 512-token limit by at most 20 tokens (mean 9); the cut tail is inside the 30-token overlap with the next chunk.

| Metric | Baseline | + context header |
|---|---|---|
| **recall@5** | 14/24 = 0.58 | **18/24 = 0.75** |
| **MRR** | **0.42** | 0.39 |
| recall@5, table (8) | 5/8 | 7/8 |
| recall@5, note (6) | 6/6 | 6/6 |
| recall@5, prose (10) | 3/10 | 5/10 |
| Refusal (unanswerable refused) | 6/6 | 6/6 |
| Answered (of 24 answerable) | 16 | 19 |
| Faithfulness (answered only) | 14/16 | 18/19 |
| Answer contains expected string | 12/24 | 16/24 |

*Retrieval rows are exact (retrieval is deterministic). Answer rows vary by 1-2 questions between runs.*

**What changed per question:** 4 misses fixed (q02, q03, q16, q21), 0 lost. But six hits moved *down* the ranking (q05 and q06 from rank 1 to 5; q08, q11, q13, q14 from 1 to 2) and five moved up, so MRR fell slightly while recall rose.

**Still missed (6):** q07, q17, q19, q20, q22, q24, all prose or a table without a distinctive label.

## Experiment 2: context header + derived period (Nov 13, 2026)

**Change (one thing, on top of Experiment 1):** the header also says which calendar period the fiscal quarter ended in, from a plain lookup table (`QUARTER_PERIOD` in `rag/config.py`): `Tata Consultancy Services (TCS) | FY27-Q2, quarter ended September 2026 | earnings call transcript`. Collection `FILINGS_CTX_PERIOD`. Questions are phrased "quarter ended September 2026", which `FY27-Q2` alone cannot match.

| Metric | Baseline | + context header | + header and period |
|---|---|---|---|
| **recall@5** | 14/24 = 0.58 | 18/24 = 0.75 | **19/24 = 0.79** |
| **MRR** | 0.418 | 0.391 | **0.424** |
| recall, table (8) | 5/8 | 7/8 | **8/8** |
| recall, note (6) | 6/6 | 6/6 | 6/6 |
| recall, prose (10) | 3/10 | 5/10 | 5/10 |
| Refusal | 6/6 | 6/6 | 6/6 |
| Answered (of 24) | 16 | 19 | 20 |
| Faithfulness (answered only) | 14/16 | 18/19 | 15/20 |
| Answer contains expected string | 12/24 | 16/24 | 17/24 |

*Retrieval rows are exact. Answer rows vary by 1-2 questions between runs.*

**What the period did:** it fixed the period-confusion cases (q05 back from rank 5 to 1, q11 back to 1) and found the one table the plain header missed (q07). MRR recovered from 0.391 to 0.424, slightly above baseline, while keeping the recall gain. Every table question is now retrieved. Some ranks still slipped by one (q01, q13).

**Still missed (5, all prose):** q17, q19, q20, q22, q24. These are single sentences from long call transcripts ("deposit growth of Rs 1,57,000 crores", "ARPU came in at Rs.264"); the header gives company and quarter but the sentence itself is generic, and each transcript has hundreds of similar chunks. A different kind of fix is needed (smaller or sentence-level chunks, or reranking) and is out of scope for this experiment.

**Faithfulness fell to 15/20, and the cause is visible:** now that more table questions are answered, the model states units that are not in the chunk. It writes "crore" or "in the units of ..." beside numbers from tables that carry no unit text (q02, q04, q06), and "per user per month" for ARPU (q23); the judge flags each as unsupported. One failure (q03) is a judge parse error. So this is a real answer-quality finding, not noise: the answer prompt should say to quote figures exactly as written and add no units the chunk does not state. Not yet fixed.

## Experiment 3: answer prompt stops adding units (Nov 13, 2026)

**Change (answer side only; retrieval is identical to Experiment 2):** one added sentence in the system prompt: *"Quote figures exactly as they appear in the chunk. Do not add units (crore, million, per month) or other details the chunk does not state."* `temperature=0` could not be applied: `anthropic` 2.8.0 exposes no `temperature` parameter on `messages.create` or `messages.parse` for this model, so answer metrics keep their +/-1-2 question run-to-run variation.

| Answer metric | Before the rule | After the rule |
|---|---|---|
| Answered (of 24) | 20 | 18 |
| Faithfulness (answered only) | 15/20 = 0.75 | **16/18 = 0.89** |
| Answer contains expected string | 17/24 | 16/24 |
| Citations valid | 20/20 | 18/18 |
| Refusal | 6/6 | 6/6 |

**Trade-off:** faithfulness recovered (the "crore" / "per user per month" additions are gone), but two fewer questions were answered, so the model refuses slightly more when a figure has no stated unit. Given the run-to-run variation this is within noise for answered / expected-string, but the faithfulness gain matches the cause I identified. Remaining unfaithful: q03 (judge reasoning says the figures are supported, so likely a judge inconsistency) and q23 (added the word "increase", which the cut-off chunk does not state).

## Index choice

Measured on `FILINGS_CTX_PERIOD`: forcing exact search returned the same top-5 as the default on 30/30 queries at the same latency (median ~260 ms, mostly network to the cloud cluster). 6,439 chunks is ~9.7 MB of dense vectors, just under Qdrant's 10,000 KB threshold, so at this size the index changes nothing. Chosen for built-in hybrid (dense + BM25 with RRF);

## RAG vs long-context (Nov 13, 2026)

**Setup:** same 30 questions, same model (`claude-haiku-5-5`), same prompt rules, same strict "answer contains the expected string" check. Long-context gets no retrieval: for each question the **whole filing that holds the answer** goes in the prompt (all filings of that company, quarter and kind; the 6 unanswerable questions get the filing of the company they ask about). This is the **best case for long-context**: it is told which filing to read, which RAG had to work out from the question. **This comparison was run by hand** with throwaway scripts that are not kept in the repo (one call per question to the Messages API, token counts and latency read from each response, answers checked against the same expected strings), so it is not reproducible from the repo. The RAG side wrapped the real `answer_query` to record its token usage and latency.

| | RAG (final config) | Long-context (oracle filing) |
|---|---|---|
| Answered (of 24 answerable) | 18 | **24** |
| Answer contains expected string | 15/24 | **24/24** |
|   table / note / prose | 8 / 4 / 3 | 8 / 6 / **10** |
| Unanswerable refused | 6/6 | 6/6 |
| Prompt tokens per question (median / max) | 4,358 / 5,177 | 35,772 / 274,174 |
| Latency per question (median / max) | 2.1 s / 3.8 s | 1.9 s / 5.5 s |
| **Cost per question, no caching** | **$0.00053** | $0.00962 |
| Cost per question, with prompt caching | $0.00053 | $0.01060 |
| Cost for all 30 questions | $0.016 | $0.289 (no cache), $0.318 (cache) |
| Rs per question (at an **assumed** Rs 90/USD, not looked up) | 0.048 | 0.87 (no cache), 0.95 (cache) |

**Verdict: long-context wins on accuracy, and it is not close on this set (24/24 vs 15/24 on the strict check), at about 18x the cost without caching and 20x with it. It was not slower.**

The 9 questions only long-context got right split three ways:
- **5 retrieval misses** (q17, q19, q20, q22, q24): the answer chunk never reached the model. RAG's ceiling is retrieval recall (0.79), and these are prose buried in long transcripts.
- **3 right answers that fail the strict check** (q09, q13, q21): RAG said "INR 12 per equity share" (expected "Equity Share"), "2.35 ... from 2.13" (expected "2.35 from 2.13"), and "253.39 billion Rupees" (expected "25,339", the same quantity restated in a different unit). So the real accuracy gap is smaller than 24 vs 15: closer to 24 vs 18.
- **1 genuine answer-stage miss** (q15): the chunk was retrieved (rank 3) but the model still answered "Not disclosed".

**Why this still is not "so don't build RAG":**
- The comparison is deliberately favourable to long-context (oracle filing). A real system does not know which filing holds the answer, and the whole corpus is ~2.7M tokens (largest filing ~274k, Infosys alone ~1M), which does not fit in one prompt. Some retrieval step (even filing-level) is unavoidable, and the cost of *that* step is not in the long-context numbers.
- Cost scales with filing size, not with question: the single largest prompt (INFY results, 274k tokens) is priced in the $0.50/$2.50 tier because it exceeds 100k tokens, while a RAG prompt stays ~4k tokens regardless of corpus size.
- At 30 questions over ~20 filings the total bill is cents either way. The 18x ratio matters at scale, not here.

**Caching did not help:** it made long-context ~10% *more* expensive (cache writes cost 1.25x the input price, reads 0.1x). Most filings are asked about once or twice, so the write premium is rarely repaid. Caching only pays when many questions hit the same filing. (Cost assumptions: Haiku 5.5 at $0.10/$0.50 per million tokens up to a 100k-token prompt and $0.50/$2.50 above it; cache write 1.25x, cache read 0.1x, as given in the API reference.)

**Not measured for long-context:** faithfulness (no judge run). Latency is wall-clock from this machine and includes network. Prompt-token counts come from the API's own usage fields. The USD-to-INR rate is an assumption.

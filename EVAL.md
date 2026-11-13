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

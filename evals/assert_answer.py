import json


def get_assert(output, context):
    v = context["vars"]
    r = json.loads(output)

    if not context["test"]["metadata"]["answerable"]:
        refused = not r["answerable"]
        return {"pass": refused, "score": int(refused), "reason": "refused" if refused else "answered a question it should refuse",
                "named_scores": {"refusal": int(refused)}}

    retrieved = {c["chunk_id"] for c in r["chunks"]}
    correct = v["expected_contains"] in r["answer"]
    cited_ok = len(r["cited"]) > 0 and set(r["cited"]).issubset(retrieved)  # cited something, all of it retrieved
    return {"pass": correct, "score": int(correct), "reason": f"citations_valid={cited_ok}",
            "named_scores": {"answer_correct": int(correct), "citation_valid": int(cited_ok)}}

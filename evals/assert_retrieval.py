import json


def get_assert(output, context):
    v = context["vars"]

    if not context["test"]["metadata"]["answerable"]:
        return True  # nothing to retrieve, so no retrieval score

    for chunk in json.loads(output)["chunks"]:
        right_filing = (chunk["ticker"], chunk["quarter"]) == (v["expected_ticker"], v["expected_quarter"])
        if right_filing and v["expected_contains"] in chunk["text"]:
            rr = 1 / chunk["rank"]
            return {"pass": True, "score": rr, "reason": f"rank {chunk['rank']}",
                    "named_scores": {"recall@5": 1, "mrr": rr}}

    return {"pass": False, "score": 0, "reason": "not in top 5",
            "named_scores": {"recall@5": 0, "mrr": 0}}

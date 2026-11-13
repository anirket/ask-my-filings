from qdrant_client.models import Fusion, FusionQuery, Prefetch, SparseVector
from rag.config import COLLECTION_NAME, PREFETCH_LIMIT
from rag.embed import embed_query
from rag.qdrant import client


def retrieve(question: str, k: int = 5):
    dense_embedding, sparse_embedding = embed_query(query=question)

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            Prefetch(using="dense", limit=PREFETCH_LIMIT, query=dense_embedding),
            Prefetch(using="sparse", limit=PREFETCH_LIMIT, query=SparseVector(
                indices=sparse_embedding.indices.tolist(),
                values=sparse_embedding.values.tolist()
            ))
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        with_payload=True,
        limit=k + 10  # extra, so tied scores at the cut-off are sorted before we cut
    )
    # RRF scores tie often and Qdrant orders ties randomly: break them by chunk_id.
    points = sorted(response.points, key=lambda p: (-p.score, p.payload["chunk_id"]))
    return points[:k]


# SANITY

# if __name__ == "__main__":
#     questions = [
#         "What was TCS net profit in the September 2026 quarter?",
#         "What did Reliance management say about capex?",
#         "What is the gross NPA ratio for SBI?",
#         "What was Bajaj Finance assets under management in Q2 FY27?",
#         "What guidance did Infosys give for revenue growth?",
#         "What did HDFC Bank say about cryptocurrency exposure?",
#     ]
#     for q in questions:
#         print("\n====", q)
#         for p in retrieve(q):
#             print(round(p.score, 3), p.payload["ticker"], p.payload["quarter"], p.payload["text"][:100])
#     client.close()

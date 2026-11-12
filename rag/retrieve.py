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
        limit=k
    )
    return response.points


if __name__ == "__main__":
    questions = [
        "What was TCS net profit in the September 2026 quarter?",
        "What did Reliance management say about capex?",
        "What is the gross NPA ratio for SBI?",
        "What was Bajaj Finance assets under management in Q2 FY27?",
        "What guidance did Infosys give for revenue growth?",
        "What did HDFC Bank say about cryptocurrency exposure?",
    ]
    for q in questions:
        print("\n====", q)
        for p in retrieve(q):
            print(round(p.score, 3), p.payload["ticker"], p.payload["quarter"], p.payload["text"][:100])
    client.close()

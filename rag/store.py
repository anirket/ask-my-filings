# INDEX CHOICE (measured Nov 13, 2026, on the FILINGS_CTX_PERIOD collection)
# Qdrant only offers HNSW (the exact-vs-IVFFlat choice belongs to pgvector/FAISS), so the real question is
# whether the index matters at our size. 6,439 chunks = ~9.7 MB of dense vectors, just under Qdrant's
# 10,000 KB indexing/full-scan threshold. Forcing exact search (SearchParams(exact=True)) returned the same
# top-5 as the default on 30/30 queries at the same latency (median ~260 ms, almost all network round trip
# to the cloud cluster), so at this size the index changes nothing: search is effectively exact.
# I chose Qdrant for built-in hybrid search (dense + BM25 fused with RRF in one query)

from qdrant_client.models import VectorParams, Distance, SparseVectorParams, Modifier, PointStruct, SparseVector
from rag.config import COLLECTION_NAME, BATCH
from rag.embed import dense_embedding_model, embed_chunks
from rag.chunk import chunk_all, context_header
from rag.qdrant import client
import uuid


def delete_collection():
   if client.collection_exists(collection_name=COLLECTION_NAME):
        client.delete_collection(collection_name=COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' deleted.")
   else:
        print(f"Collection '{COLLECTION_NAME}' does not exist.")

def build_collection():
    delete_collection()
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": VectorParams(size=dense_embedding_model.embedding_size, distance=Distance.COSINE)
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(modifier=Modifier.IDF)
        }
    )
    return client

def load():
    chunks = chunk_all()

    for start in range(0, len(chunks), BATCH):
        batch = chunks[start: start + BATCH]

        texts = [context_header(c.metadata) + "\n" + c.page_content for c in batch]  # header is embedded, not stored
        dense_embedding, sparse_embedding = embed_chunks(texts=texts)

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk.metadata['chunk_id'])),
                    vector={
                        "dense": dense_embedding[i].tolist(),
                        "sparse": SparseVector(
                            indices=sparse_embedding[i].indices.tolist(),
                            values=sparse_embedding[i].values.tolist()
                        )
                    },
                    payload={
                        **chunk.metadata,
                        "text": chunk.page_content
                    }
                )
                for i, chunk in enumerate(batch)
            ]
        )

        print(f"{start + len(batch)}/{len(chunks)}")

if __name__ == "__main__":
    build_collection() 
    load()
    print(client.count(COLLECTION_NAME))
    client.close()
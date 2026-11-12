import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, SparseVectorParams, Modifier, PointStruct, SparseVector
from rag.config import COLLECTION_NAME, BATCH
from rag.embed import dense_embedding_model, embed_chunks
from rag.chunk import chunk_all
import uuid



load_dotenv()

client = QdrantClient(
    url="https://6674d2ff-891b-441a-b6d2-2a5bc8fe6e71.us-west-1-0.aws.cloud.qdrant.io",
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=60
)
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

        texts = [c.page_content for c in batch]
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
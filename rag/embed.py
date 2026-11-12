from fastembed import SparseTextEmbedding, TextEmbedding

dense_embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
sparse_embedding_model = SparseTextEmbedding(model_name="Qdrant/bm25")

def embed_chunks(texts: list[str]):
    dense_embedding = list(dense_embedding_model.embed(texts))
    sparse_embedding = list(sparse_embedding_model.embed(texts))
    return (dense_embedding, sparse_embedding)

def embed_query(query):
    PREFIX = "Represent this sentence for searching relevant passages: "
    dense_embedding = next(dense_embedding_model.query_embed(query=PREFIX + query)).tolist()
    sparse_embedding = next(sparse_embedding_model.query_embed(query))

    return (dense_embedding, sparse_embedding)
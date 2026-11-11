from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from transformers import AutoTokenizer
from pathlib import Path
import json
import random

# Count with bge's own tokenizer: bge truncates at 512 of ITS tokens,
tok = AutoTokenizer.from_pretrained('BAAI/bge-small-en-v1.5')

def n_tokens(text: str) -> int:
    return len(tok.encode(text, add_special_tokens=False))


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    length_function=n_tokens,
    add_start_index=True, # records where each chunk starts in the filing
)


def chunk_filing(txt_path: Path, meta_path: Path):
    content = txt_path.read_text(encoding='utf-8')
    raw = json.loads(meta_path.read_text(encoding='utf-8'))

    # keep only necessary data
    meta_data = {
        "newsid": raw["NEWSID"],
        "ticker": raw["ticker"],
        "kind": raw["kind"],
        "quarter": raw["quarter"],
        "date": raw["NEWS_DT"],
        "headline": raw["HEADLINE"],
    }

    chunks = text_splitter.split_documents(
        [
            Document(
                page_content=content, 
                metadata=meta_data
            )
        ]
    )

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{meta_data['newsid']}-{i}"
    return chunks


def chunk_all():
    base_path = Path('data/filings')
    all_chunks = []
    for txt_path in sorted(base_path.glob('*/*/*.txt')):
        json_path = txt_path.with_suffix('.json')
        chunk = chunk_filing(txt_path, json_path)
        all_chunks.extend(chunk)
    return all_chunks


if __name__ == "__main__":
    # sanity check
    chunks = chunk_all()
    lengths = [n_tokens(c.page_content) for c in chunks]
    print(f"chunks: {len(chunks)}  avg tokens: {sum(lengths) // len(lengths)}  max: {max(lengths)}")

    for c in random.sample(chunks, 3):
        print("\n----", c.metadata["chunk_id"])
        print(c.page_content)

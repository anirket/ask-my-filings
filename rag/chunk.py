import json
import random
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from pathlib import Path
from transformers import AutoTokenizer


tok = AutoTokenizer.from_pretrained('BAAI/bge-small-en-v1.5')

def get_size (text):
    return len(tok.encode(text, add_special_tokens=False))


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=30,
    length_function=get_size,
    add_start_index=True
)

def chunk_filing(txt_path, meta_path):
    content = txt_path.read_text(encoding='utf-8')
    meta_content = json.loads(meta_path.read_text(encoding='utf-8'))

    meta_data = {
        'newsid': meta_content['NEWSID'],
        'ticker': meta_content['ticker'],
        'kind': meta_content['kind'],
        'quarter': meta_content['quarter'],
        'date': meta_content['NEWS_DT'],
        'headline': meta_content['HEADLINE'],
    }

    document = [Document(
        page_content=content,
        metadata=meta_data
    )]

    chunks =  text_splitter.split_documents(document)

    for i, chunk in  enumerate(chunks):
        chunk.metadata['chunk_id'] = f"{meta_data['newsid']}-{i}"

    return chunks


def chunk_all():
    base_path = Path("data/filings")
    all_chunks = []
    for txt_path in sorted(base_path.glob("*/*/*.txt")):
        json_path = txt_path.with_suffix('.json')
        all_chunks.extend(chunk_filing(txt_path, json_path))
    return all_chunks


if __name__ == "__main__":
    chunks = chunk_all()
    lengths = [get_size(c.page_content) for c in chunks]
    print(f"chunks: {len(chunks)}  avg tokens: {sum(lengths) // len(lengths)}  max: {max(lengths)}")

    for c in random.sample(chunks, 3):
        print("\n----", c.metadata['chunk_id'])
        print(c.page_content)
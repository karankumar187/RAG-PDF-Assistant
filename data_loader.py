from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from openai import OpenAI
import os

EMBED_DIM = 1536
EMBED_MODEL = "openai/text-embedding-3-small"

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, 'text', None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks

def embded_texts(texts: list[str]) -> list[list[float]]:
    """Generate real semantic embeddings via OpenRouter."""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]

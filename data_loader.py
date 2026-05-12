from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
import numpy as np

EMBED_DIM = 3072

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, 'text', None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks

def embded_texts(texts: list[str]) -> list[list[float]]:
    """Generate simple deterministic embeddings for texts using text-embedding-3-large dimension."""
    embeddings = []
    for text in texts:
        hash_val = hash(text)
        np.random.seed(abs(hash_val) % (2**31))
        embedding = np.random.randn(EMBED_DIM).astype(float).tolist()
        embeddings.append(embedding)
    return embeddings

from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def load_chunks(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip(): continue
            row = json.loads(line)
            required = {"chunk_id", "doc_name", "page_number", "chapter", "article", "clause", "text"}
            if not required.issubset(row): raise ValueError(f"JSONL line {n} missing keys: {required-set(row)}")
            if not row["text"].strip(): continue
            rows.append(row)
    return rows


def index_bm25(chunks: list[dict[str, Any]], dest: Path) -> None:
    from rank_bm25 import BM25Okapi
    import pickle, re
    tokens = [re.findall(r"\w+", c["text"].lower(), re.UNICODE) for c in chunks]
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f: pickle.dump((chunks, BM25Okapi(tokens)), f)


def index_qdrant(chunks: list[dict[str, Any]], path: Path, model_name: str) -> None:
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient, models
    model = SentenceTransformer(model_name)
    client = QdrantClient(path=str(path))
    collection = "rag_chunks"
    if client.collection_exists(collection): client.delete_collection(collection)
    vectors = model.encode([c["text"] for c in chunks], normalize_embeddings=True, show_progress_bar=True)
    client.create_collection(collection_name=collection, vectors_config=models.VectorParams(size=vectors.shape[1], distance=models.Distance.COSINE))
    points = [models.PointStruct(id=i+1, vector=vectors[i].tolist(), payload=c) for i,c in enumerate(chunks)]
    for start in range(0, len(points), 128): client.upsert(collection_name=collection, points=points[start:start+128])


def build_indexes(jsonl: Path, bm25_path: Path, qdrant_path: Path, model_name: str, no_vector=False):
    chunks = load_chunks(jsonl)
    index_bm25(chunks, bm25_path)
    if chunks and not no_vector: index_qdrant(chunks, qdrant_path, model_name)
    return {"chunks_indexed": len(chunks), "bm25": str(bm25_path), "qdrant": None if no_vector else str(qdrant_path)}

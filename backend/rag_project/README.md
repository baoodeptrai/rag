# RAG pipeline

This package owns the shared TV1/TV2 pipeline: PDF/DOCX extraction, chunk metadata, BM25 and Qdrant indexing, hybrid retrieval, and grounded answers. Setup and run instructions for the full project are in the [repository README](../../README.md).

Run the pipeline from the `backend/` directory after activating its Python environment:

```powershell
python -m rag_project.pipeline
```

Inputs are read from `backend/data/raw`; chunks and BM25 are written to `backend/data/processed`, and Qdrant lives in `backend/data/qdrant`. Put only authorized source documents in the raw folder. No evaluation metrics are claimed until `test_questions.csv` is run against a real, approved document collection.

The public function is `rag_project.ask_rag(user_query: str)`. Its stable response contains `answer`, `citations`, `confidence_score`, and `retrieved_chunks`; `confidence_score` is an internal retrieval estimate, not a calibrated probability.

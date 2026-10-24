# Backend API and RAG

This folder contains the FastAPI application (`app/`), the TV1/TV2 RAG package (`rag_project/`), and the shared data directories (`data/`). Follow the setup instructions in the [repository README](../README.md).

Run `python run.py` from this directory. The API is available at `http://127.0.0.1:8000`; OpenAPI docs are at `/docs`.

Add PDF/DOCX documents to `data/raw` or upload them with `POST /api/admin/upload`, then run `python -m rag_project.pipeline` from this directory to rebuild BM25 and Qdrant indexes. Chat citations are assembled from retrieved chunks only.

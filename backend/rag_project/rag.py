from __future__ import annotations
import json, logging, os, pickle, re, urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
BACKEND_ROOT = Path(__file__).resolve().parents[1]
# Do not depend on the process working directory: start the API from any folder
# and still load the one intended configuration file.
load_dotenv(BACKEND_ROOT / ".env")
# Runtime inference must use locally cached weights and local Ollama only.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
logger = logging.getLogger(__name__)

NO_EVIDENCE = "Chưa tìm thấy thông tin phù hợp trong tài liệu hiện có."


def _tokens(s: str): return re.findall(r"\w+", s.lower(), re.UNICODE)


@lru_cache(maxsize=2)
def _embedding_model(model_name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def hybrid_search(query: str, bm25_path: Path, qdrant_path: Path, model_name: str,
                  top_k: int = 5, rrf_k: int = 60) -> tuple[list[dict[str, Any]], float]:
    with bm25_path.open("rb") as f: chunks, bm25 = pickle.load(f)
    if not chunks or bm25 is None or not query.strip(): return [], 0.0
    bm_scores = bm25.get_scores(_tokens(query))
    bm_order = sorted(range(len(chunks)), key=lambda i: float(bm_scores[i]), reverse=True)
    bm_rank = {idx: rank+1 for rank, idx in enumerate(bm_order[:max(top_k*4, 20)])}
    vec_rank, vec_sim = {}, {}
    if qdrant_path.exists():
        from qdrant_client import QdrantClient
        model = _embedding_model(model_name)
        qvec = model.encode(query, normalize_embeddings=True).tolist()
        client = QdrantClient(path=str(qdrant_path))
        if client.collection_exists("rag_chunks"):
            hits = client.query_points(collection_name="rag_chunks", query=qvec, limit=max(top_k*4, 20)).points
            ids = {c["chunk_id"]: i for i,c in enumerate(chunks)}
            for rank, hit in enumerate(hits, 1):
                idx = ids.get(hit.payload.get("chunk_id"))
                if idx is not None: vec_rank[idx] = rank; vec_sim[idx] = float(hit.score)
        client.close()
    candidates = set(bm_rank) | set(vec_rank)
    scores = {i: (1/(rrf_k+bm_rank[i]) if i in bm_rank else 0) + (1/(rrf_k+vec_rank[i]) if i in vec_rank else 0) for i in candidates}
    ranked = sorted(candidates, key=lambda i: scores[i], reverse=True)[:top_k]
    out = []
    for i in ranked:
        row = dict(chunks[i]); row["retrieval_score"] = round(scores[i], 6)
        row["vector_similarity"] = round(vec_sim[i], 4) if i in vec_sim else None
        row["bm25_rank"] = bm_rank.get(i); out.append(row)
    best_vec = max(vec_sim.values(), default=0.0)
    best_bm = float(bm_scores[bm_order[0]]) if bm_order else 0.0
    # Conservative evidence gate: at least one meaningful lexical or semantic match.
    evidence = best_vec >= float(os.getenv("MIN_VECTOR_SIMILARITY", "0.30")) or best_bm >= float(os.getenv("MIN_BM25_SCORE", "1.0"))
    return (out if evidence else []), max(best_vec, min(best_bm/10, 1.0))


def _call_local_model(model: str, messages: list[dict[str, str]], num_predict: int,
                      response_format: dict[str, Any] | str | None = None) -> str:
    base = os.getenv("LLM_BASE_URL", "").rstrip("/")
    if not (base and model):
        raise RuntimeError("Chưa cấu hình LLM_BASE_URL và model local trong backend/.env")
    parsed = urlparse(base)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Chế độ offline chỉ cho phép Ollama chạy trên máy này (localhost)")
    # Qwen3 enables a separate thinking trace by default. Disable it for the
    # product's short routing/grounded-answer turns to avoid spending the whole
    # request timeout on hidden reasoning before any user-facing text appears.
    body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        **({"format": response_format} if response_format else {}),
        "options": {"temperature": 0, "num_predict": num_predict, "num_ctx": 2048},
    }, ensure_ascii=False).encode()
    # Use Ollama's native chat endpoint because `think` is a native Ollama API
    # option; the OpenAI-compatible endpoint does not document this field.
    local_api = f"{parsed.scheme}://{parsed.netloc}/api/chat"
    req = urllib.request.Request(local_api, data=body, headers={"Content-Type": "application/json"})
    timeout_seconds = float(os.getenv("LLM_TIMEOUT", "0"))
    with urllib.request.urlopen(req, timeout=timeout_seconds or None) as response:
        data = json.load(response)
    content = data.get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("Ollama hoàn tất request nhưng không trả nội dung trong message.content")
    return content


def _call_llm(query: str, chunks: list[dict[str, Any]]) -> str:
    model = os.getenv("LLM_MODEL", "").strip()
    context = "\n\n".join(f"[{c['chunk_id']}] {c['doc_name']} | trang={c.get('page_number')} | {c.get('chapter')} | {c.get('article')} | {c.get('clause')}\n{c['text'][:1800]}" for c in chunks[:2])
    prompt = ("NGỮ CẢNH (chỉ dùng làm nguồn dữ kiện):\n"
              f"{context}\n\nCÂU HỎI: {query}")
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    raw = _call_local_model(model, [
        {"role": "system", "content": (
            "Bạn trả lời câu hỏi về quy chế sinh viên bằng tiếng Việt. "
            "Chỉ xuất một câu trả lời trực tiếp, tối đa 2 câu. "
            "Chỉ dùng dữ kiện trong ngữ cảnh; không trình bày suy luận hay nhắc lại câu hỏi. "
            "Nếu thiếu căn cứ, nói rõ chưa tìm thấy thông tin trong tài liệu."
        )},
        {"role": "user", "content": prompt},
    ], num_predict=160, response_format=schema)
    try:
        answer = json.loads(raw).get("answer", "").strip()
    except (json.JSONDecodeError, AttributeError):
        answer = ""
    if not answer:
        raise RuntimeError("Ollama không trả được câu trả lời JSON hợp lệ")
    return answer


def ask_rag(user_query: str) -> dict[str, Any]:
    result = {"answer": NO_EVIDENCE, "citations": [], "confidence_score": 0.0, "retrieved_chunks": []}
    try:
        if not isinstance(user_query, str) or not user_query.strip(): return result
        root = Path(os.getenv("RAG_DATA_DIR", str(BACKEND_ROOT / "data" / "processed")))
        qdrant_path = Path(os.getenv("QDRANT_PATH", str(BACKEND_ROOT / "data" / "qdrant")))
        # Keep one Qwen call per request. On a CPU-only 4B setup, asking the
        # same model to rewrite the query and then answer doubles latency.
        # Hybrid search uses the original Vietnamese query; Qwen analyzes the
        # retrieved evidence in the single answer-generation call below.
        top_k = int(os.getenv("TOP_K", "3"))
        bm25_path = root/"bm25.pkl"
        embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        # The original question drives both lexical and vector retrieval. Qwen
        # is called once after retrieval to synthesize a grounded answer.
        chunks, confidence = hybrid_search(user_query, bm25_path, qdrant_path, embedding_model, top_k)
        if not chunks: return result
        result["retrieved_chunks"] = chunks
        result["confidence_score"] = round(confidence, 4) # internal estimate; not a calibrated probability
        try:
            answer = _call_llm(user_query, chunks)
        except Exception as exc:
            # Keep the chat endpoint usable, but record the provider failure in the
            # backend console so HTTP 200 does not hide Groq authentication/rate errors.
            if isinstance(exc, urllib.error.HTTPError):
                try:
                    provider_error = exc.read().decode("utf-8", errors="replace")[:1500]
                except Exception:
                    provider_error = "(không đọc được nội dung lỗi từ nhà cung cấp)"
                logger.error("LLM provider returned HTTP %s: %s", exc.code, provider_error)
                error_label = f"HTTP {exc.code}"
            else:
                logger.exception("LLM provider request failed (%s)", type(exc).__name__)
                error_label = type(exc).__name__
            answer = f"Không thể tạo câu trả lời bằng mô hình hiện tại ({error_label}). Vui lòng kiểm tra các đoạn nguồn được truy xuất."
        result["answer"] = answer or NO_EVIDENCE
        # Do not show weak retrieval matches as evidence when the model refused
        # because the indexed documents do not contain an answer.
        refused_for_missing_evidence = result["answer"].casefold().startswith((
            NO_EVIDENCE.casefold(),
            "chưa tìm thấy thông tin",
            "chưa tìm thấy căn cứ",
        ))
        result["citations"] = [] if refused_for_missing_evidence else [
            {k: c.get(k) for k in ("chunk_id", "doc_name", "page_number", "chapter", "article", "clause")}
            for c in chunks
        ]
        return result
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

from pathlib import Path
from .ingest import build_chunks
from .indexing import build_indexes


def main():
    base = Path(__file__).resolve().parents[1]
    report = build_chunks(base/"data/raw", base/"data/processed/chunks.jsonl")
    print("Ingestion:", report)
    if report["chunks"]:
        print("Indexes:", build_indexes(base/"data/processed/chunks.jsonl", base/"data/processed/bm25.pkl", base/"data/qdrant", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"))
        from .rag import ask_rag
        for i, query in enumerate(["Điều kiện đăng ký tín chỉ là gì?", "Sinh viên được bảo lưu kết quả học tập không?"]*5, 1):
            print(f"\nQUERY {i}: {query}\n{ask_rag(query)}")
    else: print("Chưa có tài liệu PDF/DOCX trong data/raw; chưa tạo chỉ mục hoặc truy vấn thử.")

if __name__ == "__main__": main()

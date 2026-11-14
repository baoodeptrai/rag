# Báo cáo tóm tắt đánh giá RAG offline

**Ngày benchmark:** 13/11/2026  
**Model sinh câu trả lời:** Qwen3 4B qua Ollama local  
**Phạm vi:** RAG offline trên một sổ tay sinh viên PDF, 75 trang.

## 1. Kiến trúc và chức năng đã hoàn thành

Hệ thống dùng một model local duy nhất là Qwen3 4B, chạy qua Ollama tại `http://127.0.0.1:11434`. Backend RAG nhận câu hỏi, truy xuất các đoạn tài liệu phù hợp, cung cấp ngữ cảnh cho model và trả lời kèm citation. Khi tài liệu không có đủ bằng chứng hoặc câu hỏi ngoài phạm vi, hệ thống từ chối trả lời.

Các chức năng đã có:

- Chat API và giao diện chat.
- BM25-only, Dense-only và Hybrid RRF.
- Citation theo tên tài liệu, trang và chunk.
- Từ chối câu hỏi thiếu căn cứ hoặc ngoài phạm vi.
- Pipeline ingest PDF/DOCX, chunking, metadata, chỉ mục vector và BM25.
- Quản lý cập nhật dữ liệu theo hash: tài liệu thay thế hoàn toàn phải xóa chunk/chỉ mục cũ trước khi lập chỉ mục lại; tài liệu chỉnh sửa được nhận diện và cập nhật theo phiên bản để tránh trùng lặp.

## 2. Corpus và Golden Dataset v2

- Corpus: 01 sổ tay sinh viên PDF, 75 trang.
- Structure-aware chunking: 87 chunks.
- Golden Dataset v2 draft: 100 câu hỏi không trùng.
  - 70 câu có bằng chứng trong tài liệu.
  - 15 câu thuộc chủ đề nhưng thiếu căn cứ trong corpus.
  - 15 câu ngoài phạm vi.

Mỗi câu có ID, câu hỏi, nhãn, đáp án chuẩn hoặc lý do từ chối; nhóm có bằng chứng có tài liệu, trang và chunk chuẩn. Dataset này là tập đánh giá, không phải dữ liệu huấn luyện. Toàn bộ nhãn hiện cần cross-review độc lập trước khi được xem là ground truth chính thức.

## 3. Câu hỏi nghiên cứu

Trên cùng corpus và 70 câu có bằng chứng, BM25-only, Dense-only và Hybrid RRF khác nhau thế nào về khả năng đưa chunk bằng chứng chuẩn vào top 5? Fixed-size chunking có cải thiện so với structure-aware chunking khi dùng cùng BM25-only không?

| Câu hỏi | Baseline | Phương pháp được đánh giá | Chỉ số |
|---|---|---|---|
| Phương pháp nào tìm bằng chứng chuẩn tốt nhất? | BM25-only, Dense-only | Hybrid RRF | Recall@5, HitRate@5, MRR@5, latency |
| Chunking nào tốt hơn trên corpus này? | Structure-aware | Fixed-size 600 token, overlap 80 | Recall@5, HitRate@5, MRR@5, latency |

## 4. Kết quả retrieval

Thiết lập: `k=5`, 70 câu answerable, 3 lần đo sau 1 lượt warm-up. Dense Retrieval dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` từ cache local.

| Phương pháp | Recall@5 | HitRate@5 | MRR@5 | Latency trung vị |
|---|---:|---:|---:|---:|
| BM25-only | 0,936 | 0,943 | 0,762 | 0,8 ms |
| Dense-only MiniLM | 0,607 | 0,614 | 0,521 | 23,6 ms |
| Hybrid RRF | 0,779 | 0,786 | 0,643 | 24,4 ms |

BM25-only có kết quả cao nhất trên corpus hiện tại. Hybrid RRF tốt hơn Dense-only nhưng chưa vượt BM25-only; do đó chưa thể kết luận Hybrid là phương pháp tốt nhất.

## 5. Kết quả A/B chunking

Thiết lập: cùng 70 câu answerable, BM25-only, `k=5`.

| Chunking | Số chunks | Recall@5 | HitRate@5 | MRR@5 | Latency trung vị |
|---|---:|---:|---:|---:|---:|
| Structure-aware | 87 | 0,936 | 0,943 | 0,762 | 0,498 ms |
| Fixed-size, 600 token, overlap 80 | 77 | 0,950 | 0,957 | 0,769 | 0,478 ms |

Fixed-size nhỉnh hơn nhẹ: tăng 0,014 Recall@5, 0,014 HitRate@5 và 0,007 MRR@5. Kết luận này mới đúng trên một tài liệu và nhãn draft; chưa đủ cơ sở để đổi chunking mặc định.

## 6. Smoke test Qwen3 4B local

Đã chạy 3 câu đại diện qua backend local: G001 có căn cứ, G075 thiếu căn cứ trong chủ đề và G088 ngoài phạm vi.

| Nhóm | Kết quả quan sát |
|---|---|
| Có căn cứ - G001 | Trả lời đúng 10 đến 22 tín chỉ và có citation; chưa nêu ngoại lệ học kỳ 3 nên cần chấm là chưa đầy đủ nếu ngoại lệ được yêu cầu. |
| Thiếu căn cứ - G075 | Từ chối trả lời, không trả citation. |
| Ngoài phạm vi - G088 | Từ chối câu hỏi tỷ giá, không trả citation. |

Không có request error. Median end-to-end latency là **3,63 giây** trên model đã nạp. Đây là smoke test, chưa phải đánh giá đủ 100 câu; các metric answer correctness, completeness, groundedness, citation accuracy và refusal accuracy cần được reviewer chấm sau khi chạy toàn bộ dataset.

## 7. Giới hạn và việc cần làm trước khi bảo vệ

- Chưa benchmark reranker.
- Chưa benchmark BGE-M3 hoặc Qwen Embedding trên cùng dataset.
- Chưa đánh giá Qwen đủ 100 câu và chưa có chấm thủ công độc lập.
- Golden Dataset v2 draft chưa cross-review độc lập.
- Kết quả chỉ dựa trên một corpus PDF; không suy rộng cho tài liệu khác.

## 8. Lệnh tái lập kết quả

Mở hai cửa sổ PowerShell tại thư mục gốc dự án.

**Cửa sổ 1 - khởi động hệ thống:**

```powershell
cd "D:\40 cái\TV4_RAG"
ollama serve
```

Nếu Ollama đã tự chạy thì không cần lệnh trên. Khởi động backend ở cửa sổ khác:

```powershell
cd "D:\40 cái\TV4_RAG\backend"
python run.py
```

Kiểm tra:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/v1/models
Invoke-RestMethod http://127.0.0.1:8000/health
```

**Cửa sổ 2 - chạy benchmark:**

```powershell
cd "D:\40 cái\TV4_RAG"
python backend/rag_project/evaluate_retrieval.py --run-id submission_retrieval --repeats 3 --warmup-repeats 1
python backend/rag_project/compare_chunking.py --run-id submission_chunking
python backend/rag_project/run_answer_quality_eval.py --question-ids G001,G075,G088 --timeout 150 --delay 0
```

Khi runner answer-quality hỏi xác nhận, nhập `RUN`. Kết quả được lưu trong `docs/evaluation/results/runs/<run_id>/`.

## 9. Tệp minh chứng

- `golden_dataset_v2_draft.csv`: Golden Dataset 100 câu.
- `runs/offline_v2_20261113_final/retrieval_summary.csv`: bảng benchmark retrieval.
- `runs/offline_v2_20261113_final/chunking_summary.csv`: bảng A/B chunking.
- `runs/offline_v2_20261113_final/answer_quality_smoke.csv`: kết quả smoke test Qwen.

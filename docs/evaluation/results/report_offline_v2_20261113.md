# Báo cáo đánh giá RAG offline - Golden Dataset v2 draft

**Ngày chạy:** 13/11/2026  
**Run ID:** `offline_v2_20261113_final`  
**Trạng thái:** Báo cáo sơ bộ; nhãn Golden Dataset chưa được cross-review độc lập.

## 1. Câu hỏi nghiên cứu và phạm vi

Trên cùng corpus, tập chunk và 70 câu hỏi có bằng chứng, BM25-only, Dense-only và Hybrid RRF khác nhau thế nào về khả năng đưa chunk chuẩn vào top 5? Chunking fixed-size có tốt hơn structure-aware khi dùng cùng BM25-only không?

Reranker và so sánh nhiều embedding chưa nằm trong lần chạy này. Benchmark retrieval không gọi LLM; answer-quality smoke test gọi riêng Qwen3:4b qua backend Ollama local.

## 2. Corpus, dataset và cấu hình

- **Nguồn:** một PDF `so-tay-sinh-vien-2026-20260908101355-e.pdf`, 75 trang.
- **Chunks đang dùng:** 87 structure-aware chunks; SHA-256 `60e0131fdc723f15b8bb78fcdcd89fa0c8cd8d62e3b41b3a0181d4712db4c972`.
- **PDF SHA-256:** `0071A35EC323F65EF6268DDBA82C212A64343810B916D982195AC49D13AEC876`.
- **Golden Dataset v2 draft:** 100 câu, 100 câu hỏi duy nhất: 70 có bằng chứng, 15 thuộc chủ đề nhưng thiếu căn cứ, 15 ngoài phạm vi. Cả 100 dòng đang `pending_independent_cross_review`.
- **Retrieval:** multilingual MiniLM `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, `k=5`, RRF `k=60`, 3 lần đo và 1 lần warm-up; embedding chạy từ cache local.
- **Phần cứng:** Intel Core 7 150U, RAM 15.7 GB, Intel Graphics tích hợp; Ollama báo Qwen3:4b chạy 100% CPU, context 2048.

Golden Dataset là tập **đánh giá**, không phải dữ liệu huấn luyện. G059 được chuyển từ nhóm từ chối sang answerable vì tài liệu nói học bổng được xét theo chỉ tiêu và xếp kết quả từ cao xuống. G064 chép URL đúng theo PDF (`portal.vau.edu.vn`); cần kiểm tra lỗi tên miền với nguồn chính thức trước khi nộp. Nhãn thiếu căn cứ và ngoài phạm vi cũng cần người rà soát độc lập.

## 3. Retrieval benchmark: BM25, Dense và Hybrid RRF

| Phương pháp | n | Recall@5 | HitRate@5 | MRR@5 | Median retrieval latency |
|---|---:|---:|---:|---:|---:|
| BM25-only | 70 | 0.936 | 0.943 | 0.762 | 0.8 ms |
| Dense-only | 70 | 0.607 | 0.614 | 0.521 | 23.6 ms |
| Hybrid RRF | 70 | 0.779 | 0.786 | 0.643 | 24.4 ms |

Trên bộ này, BM25 có kết quả cao nhất. Hybrid RRF cải thiện so với Dense-only nhưng thấp hơn BM25 0.157 Recall@5; vì vậy chưa có bằng chứng rằng Hybrid tốt hơn baseline từ khóa. Trong top 5, BM25 tìm thấy gold ở 66/70 câu, Hybrid ở 55/70, Dense ở 43/70. Hybrid bỏ lỡ 12 câu mà BM25 tìm được; chỉ có 1 câu Hybrid tìm được mà BM25 bỏ lỡ; 3 câu cả BM25 lẫn Hybrid đều bỏ lỡ.

Đây là so sánh mô tả trên một tài liệu và nhãn còn provisional. Chưa có kiểm định thống kê hay corpus thứ hai; không khái quát kết quả sang tài liệu khác.

## 4. Chunking A/B

Cùng 70 câu, cùng BM25-only, `k=5`; fixed-size dùng 600 token và overlap 80 token.

| Chunking | Số chunks | Recall@5 | HitRate@5 | MRR@5 | Median retrieval latency |
|---|---:|---:|---:|---:|---:|
| Structure-aware | 87 | 0.936 | 0.943 | 0.762 | 0.498 ms |
| Fixed-size | 77 | 0.950 | 0.957 | 0.769 | 0.478 ms |

Fixed-size nhỉnh hơn nhẹ trong lần chạy này: +0.014 Recall@5, +0.014 HitRate@5 và +0.007 MRR@5. Chênh lệch nhỏ và chỉ đo trên một sổ tay; cần cross-review nhãn và chạy thêm corpus trước khi đổi chunking mặc định.

## 5. Qwen local answer-quality smoke test

Chạy 3 câu đại diện qua backend `http://127.0.0.1:8000`, model `qwen3:4b`, không có request error. Median end-to-end latency là 3.63 giây trên lượt model đã nạp.

| ID | Nhóm | Quan sát đầu ra |
|---|---|---|
| G001 | Có căn cứ | Trả lời đúng 10-22 tín chỉ; chưa nêu ngoại lệ học kỳ 3 trong đáp án chuẩn, cần chấm là chưa đầy đủ nếu ngoại lệ được yêu cầu. |
| G075 | Thiếu căn cứ trong chủ đề | Từ chối trả lời và không trả citation. |
| G088 | Ngoài phạm vi | Từ chối câu hỏi tỷ giá và không trả citation. |

Đây chỉ là smoke test, **không phải đánh giá chất lượng đủ 100 câu**. Các cột answer correctness, completeness, groundedness, citation correctness và refusal correctness vẫn để trống để reviewer chấm. Một smoke test trước đó trên 5 câu cũng cho thấy câu Support VAA có câu trả lời thêm mục ngoài câu hỏi; xem CSV chi tiết ở run `offline_v2_20261113`.

## 6. Kết luận và việc còn lại

1. Retrieval baseline hiện thắng là BM25-only trên corpus này; Hybrid RRF chưa cải thiện đủ để được tuyên bố là tốt hơn.
2. Fixed-size nhỉnh hơn nhẹ trong thử nghiệm chunking này, chưa đủ cơ sở đổi mặc định.
3. Bộ v2 đạt đủ 100 câu và phân bố 70/15/15, nhưng tất cả nhãn cần cross-review độc lập. Kiểm tra đặc biệt G059, G064 và các nhãn thiếu căn cứ được đánh dấu trong dataset.
4. Cần chạy answer-quality đủ 100 câu sau khi chốt nhãn, rồi chấm thủ công câu trả lời/citation/refusal. Chưa có kết quả benchmark reranker hoặc embedding thứ hai.

## 7. Tệp và lệnh tái lập

- Dataset: [`golden_dataset_v2_draft.csv`](../golden_dataset_v2_draft.csv)
- Retrieval summary, per-question top-5 và metadata: `results/runs/offline_v2_20261113_final/`
- Chunking summary, per-question top-5 và metadata: `results/runs/offline_v2_20261113_final/`
- Qwen smoke CSV, metadata và summary: `results/runs/offline_v2_20261113_final/answer_quality_smoke*`

Chạy từ thư mục gốc sau khi có cache embedding và backend local:

```powershell
python backend/rag_project/evaluate_retrieval.py --run-id <run_id> --repeats 3 --warmup-repeats 1
python backend/rag_project/compare_chunking.py --run-id <run_id>
python backend/rag_project/run_answer_quality_eval.py --question-ids G001,G075,G088 --timeout 150 --delay 0
```

Runner answer-quality yêu cầu gõ `RUN` trước khi gửi câu hỏi. Không dùng run cũ ngày 28/10 có lỗi provider làm kết quả local; giữ run đó như lịch sử riêng.

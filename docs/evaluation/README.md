# Kế hoạch bổ sung nghiên cứu và đánh giá RAG

Phiên bản: 0.1 (28/10/2026)

## Kết quả mới nhất

Báo cáo offline trên Golden Dataset v2 draft (100 câu, 70 answerable) được xuất tại [`results/report_offline_v2_20261113.md`](results/report_offline_v2_20261113.md). Các lần chạy chi tiết có CSV từng câu và metadata trong `results/runs/offline_v2_20261113_final/`. Số liệu v1 bên dưới là lịch sử; dùng báo cáo v2 cho cấu hình local hiện tại.

## 1. Phạm vi nghiên cứu

**Câu hỏi nghiên cứu chính:** Trên cùng một bộ câu hỏi và cùng tập chunks, Hybrid Retrieval (BM25 + Dense, hợp nhất thứ hạng bằng RRF) có truy xuất được nhiều đoạn bằng chứng chuẩn ở thứ hạng cao hơn BM25-only và Dense-only hay không?

| Thành phần | Thiết lập |
|---|---|
| Baseline 1 | BM25-only trên chunks hiện tại |
| Baseline 2 | Dense-only dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` và Qdrant |
| Phương pháp đề xuất | BM25 + Dense, Reciprocal Rank Fusion (RRF), cùng corpus, top-k và câu hỏi |
| Chỉ số chính | Recall@5, HitRate@5, MRR@5; đo latency truy xuất riêng |
| Biến cần giữ cố định | Tài liệu nguồn, phiên bản chunks, tập câu hỏi, K, máy chạy và cấu hình truy vấn |

Đây là trục nghiên cứu chính để không dàn trải. Reranker chưa được xem là thành phần đã triển khai/đã chứng minh. Nhóm ghi quyết định **chưa đưa reranker vào phạm vi thực nghiệm chính** vì cần mô hình, tài nguyên và thêm vòng đánh giá; nếu còn thời gian thì chỉ thêm một thí nghiệm phụ, không suy diễn kết quả.

## 2. Chunking và chất lượng metadata

Chunking hiện tại dùng phân đoạn theo các dòng nhận diện Chương/Điều/Khoản, giới hạn khoảng 600 token và overlap 80 token. Cần đối chiếu thủ công một mẫu chunks với trang nguồn trước khi chốt benchmark. Có dấu hiệu thông tin Chương/Điều bị kế thừa sang nội dung khác trang; đây là lỗi metadata có thể làm citation sai. Tạm thời xem structure-aware vs fixed-size là **thí nghiệm phụ/kiểm tra dữ liệu**, chưa tuyên bố structure-aware tốt hơn.

Nếu chạy A/B: cùng một corpus, cùng embedding/retriever, cùng bộ câu hỏi và top-k; chỉ thay cách chia chunks. Báo Recall@5/HitRate@5/MRR@5, latency và số citation có trang/Điều khớp nguồn. Lưu hai phiên bản chunks tách biệt, không ghi đè nhau.

### Kết quả A/B v1 (lịch sử)

So sánh structure-aware và fixed-size đã chạy bằng cùng BM25-only retriever, 55 câu answerable, top-k=5, kích thước fixed 600 token và overlap 80 token. Chunks structure-aware lấy từ chỉ mục hiện có; fixed-size được tạo riêng trong bộ nhớ, không ghi đè chỉ mục chatbot.

| Cách chia | Số chunks | Recall@5 | HitRate@5 | MRR@5 | Median latency |
|---|---:|---:|---:|---:|---:|
| Structure-aware | 87 | 0.936 | 0.945 | 0.787 | 0.994 ms |
| Fixed-size | 77 | 0.955 | 0.964 | 0.792 | 0.929 ms |

Trên lần chạy này, fixed-size cao hơn nhẹ trên bộ câu hỏi hiện tại: Recall@5 và HitRate@5 tăng khoảng 0.019; MRR tăng khoảng 0.005. Đây là kết quả sơ bộ trên một tài liệu và nhãn được suy ra từ các đoạn bằng chứng của nhóm; không đủ để kết luận fixed-size tốt hơn nói chung. Thí nghiệm đo retrieval ranking, chưa đo citation accuracy hoặc chất lượng câu trả lời LLM.

Ví dụ error analysis: với câu G052 về các loại điểm hiển thị trong kết quả học tập, fixed-size đưa chunk bằng chứng vào hạng 5, còn structure-aware không đưa chunk chuẩn vào top 5. Đây là câu duy nhất làm HitRate@5 khác nhau giữa hai cách trong lần chạy này.

Lệnh chạy lại từ thư mục gốc:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\rag_project\compare_chunking.py
```

Kết quả chi tiết nằm ở `results/chunking_summary.csv` và `results/chunking_per_question.csv`.

## 3. Golden Dataset

`golden_dataset_submission.csv` là bản v1 lịch sử gồm 60 câu. Bản mới `golden_dataset_v2_draft.csv` có 100 câu: 70 answerable, 15 thiếu căn cứ trong chủ đề và 15 ngoài phạm vi. Bản v2 có cột `expected_refusal_reason`, `review_status`, `reviewer_1`, `reviewer_2` và `adjudication_note`; tất cả đang chờ cross-review độc lập, chưa phải bộ nhãn cuối cùng. Script kiểm tra bằng chứng mới theo chunk/page là `backend/rag_project/build_golden_dataset_v2.py`.

Cột `gold_evidence` là trích đoạn nguồn; `pipeline_page` là số trang PDF tính từ 1; `printed_page` là số trang in trong tài liệu khi xác định được. Cột `gold_chunk_ids` trỏ tới chunk có bằng chứng trong chỉ mục hiện tại. Các câu không có căn cứ/ngoài phạm vi được gắn `answerable=false` và không có chunk chuẩn.

Các dòng được xây từ nội dung PDF và kiểm tra tự động để bảo đảm trích đoạn khớp chunk ID/trang đã ghi. File nộp không chứa cột trạng thái hay reviewer. Việc kiểm tra chéo độc lập của thành viên là một minh chứng riêng nếu giảng viên yêu cầu; không ghi nhận xác nhận của thành viên khi chưa có xác nhận thực tế.

### Hướng dẫn gán nhãn

1. Chỉ lấy câu trả lời chuẩn từ tài liệu nguồn được duyệt, giữ ý nghĩa và các điều kiện/ngoại lệ quan trọng.
2. Ghi đoạn bằng chứng ngắn nhất đủ chứng minh câu trả lời; ghi đúng tên file, trang PDF và trang in (nếu có).
3. `gold_chunk_ids` gồm mọi chunk thực sự chứa bằng chứng sau khi kiểm tra nội dung chunk; một câu có thể có nhiều chunk.
4. Với câu không trả lời được từ tài liệu hoặc ngoài phạm vi, đáp án chuẩn là từ chối lịch sự và nêu không có căn cứ; không đánh dấu là retrieval miss nếu câu vốn không có bằng chứng.
5. Nếu nhóm thực hiện cross-review, hai người đọc độc lập trước khi xem kết quả chatbot; bất đồng được giải quyết bằng cách đọc lại trang nguồn và lưu biên bản riêng.

## 4. Định nghĩa chỉ số

- **HitRate@5:** tỷ lệ câu hỏi answerable có ít nhất một chunk bằng chứng chuẩn trong top 5.
- **Recall@5:** số chunk bằng chứng chuẩn được tìm thấy trong top 5 chia cho tổng số chunk bằng chứng chuẩn của câu hỏi; báo trung bình trên câu answerable.
- **MRR@5:** trung bình nghịch đảo thứ hạng của chunk bằng chứng chuẩn đầu tiên; không có bằng chứng trong top 5 nhận 0.
- **Citation accuracy:** số trích dẫn được xác nhận đúng tài liệu/trang/đoạn chia cho tổng trích dẫn được kiểm tra. Báo thêm tỷ lệ câu trả lời có ít nhất một citation đúng.
- **Refusal accuracy:** trên câu không có căn cứ/ngoài phạm vi, tỷ lệ hệ thống từ chối phù hợp; báo riêng tỷ lệ từ chối nhầm trên câu có căn cứ.
- **Latency:** thời gian retrieval và tổng thời gian trả lời đo riêng; ghi máy, số lần chạy và median. Không trộn thời gian tải model/lập chỉ mục vào latency truy vấn.

## 5. Quy trình benchmark retrieval

1. Dùng `golden_dataset_v2_draft.csv`; cross-review nhãn trước khi chốt kết quả báo cáo.
2. Đóng băng corpus/chunks và lưu hash/phiên bản cấu hình.
3. Chạy BM25-only, Dense-only, Hybrid RRF trên cùng 70 câu answerable, cùng top-k=5; chạy nhiều lượt để lấy median latency sau lượt warm-up.
4. Xuất từng top-5 kèm điểm/rank để kiểm tra được, tính chỉ số tự động và rà soát lỗi theo từng câu.
5. Báo số lượng mẫu `n` cạnh mọi tỷ lệ; bộ 100 câu vẫn dựa trên một sổ tay, không đại diện mọi tài liệu hay mọi dạng câu hỏi sinh viên.
6. Đánh giá câu trả lời LLM/citation/refusal riêng trên output đã lưu; không dùng câu trả lời sinh ra để sửa nhãn chuẩn.

## 6. Embedding và reranker

Embedding hiện có là multilingual MiniLM; lý do vận hành ban đầu là mô hình nhỏ, chạy local được trên CPU và hợp với tài nguyên demo. Đây là lý do triển khai, chưa phải bằng chứng chất lượng tiếng Việt vượt mô hình khác. Nếu có tài nguyên, benchmark phụ MiniLM và BGE-M3 trên cùng câu hỏi; đo retrieval metrics, thời gian encode/truy vấn và bộ nhớ. Chỉ báo số liệu sau khi chạy.

Reranker: trạng thái chưa được xác minh trong mã hiện tại. Báo cáo lần nộp này chốt ngoài phạm vi benchmark chính; không ghi “reranker cải thiện” nếu chưa chạy Hybrid vs Hybrid+reranker.

## 7. Tiến độ và phân công

Mẫu ở `progress_template.csv` để nhóm điền theo hồ sơ thật. Chưa có dữ liệu đủ tin cậy để tự điền tên, ngày bắt đầu, phần trăm hoàn thành, commit hoặc xác nhận bàn giao thành viên. Evidence nên là đường dẫn file, commit hash, ảnh/log chạy hoặc biên bản xác nhận.

## 8. Minh chứng phải bổ sung sau khi chạy

- Bảng kết quả BM25-only / Dense-only / Hybrid RRF và top-k theo từng câu.
- Bảng fixed vs structure-aware nếu nhóm quyết định thực hiện thí nghiệm phụ.
- Bảng citation/refusal được người đánh giá kiểm tra; ghi rõ số mẫu và cách chấm.
- Ảnh/log pipeline chạy, phiên bản tài liệu và cấu hình.
- Dataset đã cross-review; bảng tiến độ và xác nhận mapping thành viên–module.

## 9. Thu thập minh chứng câu trả lời, citation và refusal

Khởi động backend local, sau đó chạy `backend/rag_project/run_answer_quality_eval.py` từ thư mục gốc. Runner dùng Golden Dataset v2 draft, chỉ chấp nhận backend loopback, cho chọn câu smoke test bằng `--question-ids`, đo latency và ghi model/corpus/dataset hash vào metadata. Runner hỏi xác nhận `RUN` và không ghi đè kết quả cũ. Đã chạy smoke test Qwen local; kết quả và giới hạn nằm trong báo cáo v2. Đánh giá đủ 100 câu và chấm thủ công vẫn còn cần thực hiện.

Các cột chấm để trống có chủ ý. Với mỗi câu trả lời, reviewer điền `answer_correct`, `answer_complete`, `answer_grounded` và `system_refused`. Các cột citation trong answer CSV là **đánh giá cấp phản hồi**: đánh dấu đúng khi toàn bộ citation của phản hồi đúng ở chiều tương ứng. HTTP 200 không được xem là bằng chứng câu trả lời đúng.

### So sánh model sinh câu trả lời và báo cáo accuracy

Hiện project đã có baseline retrieval BM25/Dense/Hybrid, nhưng **chưa có benchmark so sánh model sinh câu trả lời và chưa có accuracy end-to-end được chấm đầy đủ**. Không suy ra accuracy từ `confidence_score` hoặc chỉ từ HTTP 200.

1. Rà soát độc lập các nhãn trong `golden_dataset_v2_draft.csv`; ghi reviewer và adjudication, không dùng cùng câu hỏi làm few-shot.
2. Đóng băng một bản dataset/corpus đã duyệt và lưu hash.
3. Chọn một model trả lời trong `LLM_MODEL`, giữ cùng `ORCHESTRATOR_MODEL`, embedding, corpus và prompt. Khởi động lại backend rồi chạy đủ dataset bằng `docs/evaluation/run_full_answer_eval.ps1`.
4. Lặp lại với model trả lời baseline khác; giữ cùng bộ câu hỏi và cấu hình retrieval. Runner ghi cả `LLM_MODEL` và `ORCHESTRATOR_MODEL` vào metadata để so sánh có thể kiểm tra lại.
5. Reviewer chấm từng câu trả lời/citation từ nguồn gốc; sau đó dùng `summarize_answer_quality.py` và công cụ citation ở trên để tính answer correctness, completeness, groundedness, refusal accuracy, citation accuracy và lỗi request. Báo riêng mẫu lỗi model/provider.

Golden Dataset là bộ kiểm thử, không phải training data. Few-shot mẫu hành vi trong prompt không lấy đáp án từ bộ kiểm thử để tránh rò rỉ nhãn.

Để tính độ chính xác ở cấp từng citation, tạo bảng một-dòng-mỗi-citation rồi chấm từng dòng:

```powershell
python backend/rag_project/flatten_citations.py docs/evaluation/results/<answer_run>.csv
python backend/rag_project/summarize_citations.py docs/evaluation/results/<answer_run>_citation_review.csv
python backend/rag_project/summarize_answer_quality.py docs/evaluation/results/<answer_run>.csv
python backend/rag_project/compare_answer_quality.py docs/evaluation/results/<model_a_run>.csv docs/evaluation/results/<model_b_run>.csv
```

Lệnh so sánh yêu cầu metadata cùng dataset hash, corpus hash, orchestrator model và cùng tập `question_id`; các khác biệt sẽ bị từ chối thay vì ghép số liệu không cùng điều kiện.

Refusal rate được tính riêng trên `expected_refusal=true`; false refusal tính trên `expected_refusal=false`. Khi dataset v2 có `expected_refusal_reason`, báo thêm nhóm thiếu căn cứ và ngoài phạm vi riêng. Các script loại request lỗi khỏi mẫu chấm chất lượng nhưng vẫn báo số lượng/tỷ lệ lỗi. Citation accuracy và tỷ lệ câu có citation đúng là hai chỉ số khác nhau.

**Giới hạn hiện tại:** Golden Dataset v2 còn chờ cross-review; corpus chỉ có một sổ tay. Chưa chạy answer-quality đủ 100 câu, chưa chấm thủ công citation/refusal, chưa benchmark reranker hoặc embedding thứ hai. Retrieval và chunking v2 là kết quả mô tả trên nhãn provisional, không phải kết luận có khả năng khái quát.

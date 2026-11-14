# Kế hoạch báo cáo và đánh giá bản chạy local

**Mục đích:** hoàn thiện minh chứng nghiên cứu/chất lượng cho sản phẩm chatbot RAG hiện có. Không yêu cầu huấn luyện model.

**Cập nhật 13/11/2026:** đã tạo Golden Dataset v2 draft 100 câu (70/15/15), chạy retrieval và chunking A/B, và smoke-test Qwen local. Báo cáo hiện tại ở `results/report_offline_v2_20261113.md`. Cross-review nhãn, answer-quality đủ 100 câu và chấm thủ công chưa hoàn tất.

## Tình trạng đầu vào đã xác nhận

- Sản phẩm có pipeline PDF/DOCX, chunking, BM25, Dense/Qdrant, Hybrid RRF, chat và citations.
- Cấu hình LLM hiện tại là Ollama `qwen3:4b`; đã chạy smoke-test local không có lỗi request.
- Retrieval v2 có 70 câu answerable: BM25 Recall/HitRate/MRR = 0.936/0.943/0.762; Dense = 0.607/0.614/0.521; Hybrid RRF = 0.779/0.786/0.643. Hybrid chưa vượt BM25.
- Chunking A/B v2 trên cùng 70 câu: structure-aware 87 chunks, fixed-size 77; fixed-size nhỉnh hơn nhẹ.
- Golden Dataset v2 draft có 100 câu: 70 answerable, 15 insufficient-evidence, 15 out-of-scope. Cross-review chưa ghi nhận.
- Lần answer-quality cũ có 42/60 lỗi provider; không dùng làm kết quả chất lượng model local.
- Corpus hiện tại có một PDF sổ tay. Không có cơ sở để khái quát kết quả cho nhiều loại văn bản hoặc nhiều đơn vị.

## Quyết định phạm vi nghiên cứu

**Trục chính: retrieval.**

> Trên cùng corpus, chunks và bộ câu hỏi đã rà soát, Hybrid RRF có tìm được bằng chứng chuẩn ở top-5 tốt hơn BM25-only và Dense-only không?

- Baseline: BM25-only và Dense-only.
- Phương pháp so sánh: Hybrid RRF.
- Chỉ số chính: Recall@5, HitRate@5, MRR@5. Báo median retrieval latency và `n`.
- Biến cố định: corpus/hash, phiên bản chunks, câu hỏi, gold evidence, K=5, máy, model embedding và cấu hình RRF.
- Chunking structure-aware vs fixed-size là thí nghiệm phụ; không gộp kết quả chunking vào kết luận chính.
- Reranker nằm ngoài phạm vi. Ghi lý do tài nguyên/phạm vi; không tuyên bố cải thiện khi chưa benchmark.
- Thử nghiệm query gốc vs query được Qwen chuẩn hóa là ablation phụ, không thay câu hỏi nghiên cứu chính.

## Kế hoạch Golden Dataset

Không cần training dataset cho RAG. Golden Dataset là bộ **đánh giá**, không dùng để fine-tune model.

Phiên bản v2 draft đã đạt mục tiêu **100 câu**.

| Nhóm | Mục tiêu | Cách chấm |
|---|---:|---|
| Có căn cứ trong corpus | 70 | answerability, gold answer, gold evidence, document/page/chunk IDs |
| Thuộc chủ đề nhưng corpus không trả lời | 15 | kỳ vọng từ chối do thiếu căn cứ |
| Ngoài phạm vi | 15 | kỳ vọng từ chối do ngoài phạm vi |

Bắt đầu từ 60 câu v1; phân loại lại G059 thành answerable sau khi đối chiếu đoạn xét học bổng theo chỉ tiêu, bổ sung câu có bằng chứng và nhóm câu từ chối. Tất cả dòng vẫn `pending_independent_cross_review`; G064 cần xác minh URL ghi trong PDF. Không coi bản draft là nhãn đã được con người xác nhận.

Một người rà toàn bộ nguồn và đáp án; ít nhất 30 câu được hai người gán độc lập trước khi xem kết quả chatbot. Lưu reviewer, bất đồng và cách adjudicate trong file review riêng. Sau khi corpus/chunking thay đổi, xác minh lại gold evidence và `gold_chunk_ids`. V2 đã phân loại lại G059 là answerable; G064 có ghi chú cần xác minh URL với nguồn chính thức. Tất cả các nhãn mới vẫn chờ cross-review.

## Các bước thực hiện và đầu ra

### A. Chuẩn bị dữ liệu và corpus

1. Corpus hiện dùng là một PDF sổ tay; tên và SHA-256 được lưu trong báo cáo offline v2.
2. Đã kiểm tra văn bản trích xuất và đối chiếu các bằng chứng mới với chunk/trang. Cần tiếp tục kiểm tra trực quan mẫu PDF–chunk và metadata Chương/Điều/Khoản.
3. Đóng băng phiên bản chunking. Kiểm tra mẫu chunks ở đầu/giữa/cuối tài liệu và các ranh giới Điều/Khoản.
4. Cross-review dataset v2 trước khi xem các output answer-quality tiếp theo; không sửa gold theo output model.

**Đầu ra:** manifest corpus/config; dataset v2 draft; guideline; review log và mẫu cross-review vẫn cần hoàn thiện.

### B. Chuẩn bị công cụ đánh giá

Các runner hiện đã được cập nhật để:

- cho chọn danh sách question IDs để smoke test đủ nhóm, thay vì chỉ lấy 5 dòng đầu;
- ghi latency tổng từng câu, trạng thái lỗi, model tag, corpus version và confidence retrieval;
- lưu citations, gold evidence, expected refusal và các cột chấm riêng: answer correct, answer complete, grounded, citation document/page/evidence correct, system refused; xuất thêm một bảng một-dòng-mỗi-citation để tính citation accuracy ở cấp trích dẫn, không nhầm với tỷ lệ câu trả lời có citation đúng;
- chỉ thêm trace query đã chuẩn hóa nếu nhóm quyết định chạy ablation query routing; hiện chưa có trace nội bộ, không cần sửa response API công khai cho benchmark chính;
- ghi output vào thư mục/version mới, không ghi đè kết quả lịch sử.
- thêm warm-up và số lần lặp cho retrieval latency; retrieval v2 dùng 3 lượt đo sau 1 lượt warm-up.

**Đầu ra:** runner tái lập được; raw answer-quality có các cột chấm để trống chờ reviewer.

### C. Retrieval benchmark — không gọi LLM trả lời

Đã chạy BM25-only, Dense-only, Hybrid RRF trên cùng 70 câu answerable và cùng index/chunks; `K=5`. Warm-up embedding trước latency; đo 3 lượt và báo median. Lưu top-5 theo câu, rank/score, gold match và thời gian retrieval riêng trong run `offline_v2_20261113_final`.

Đã chạy chunking A/B trên cùng câu hỏi và cùng BM25-only; kết quả nằm cùng thư mục run. Cần cross-review evidence trước khi chốt kết luận.

**Đầu ra:** retrieval summary, per-question top-k, chunking summary/per-question, error analysis. Không kết luận Hybrid tốt hơn nếu số liệu không cho thấy điều đó.

### D. Smoke test Qwen local và answer-quality benchmark

Điều kiện đầu vào: Ollama chạy local, `qwen3:4b` đã tải, embedding model có trong cache, backend dùng endpoint loopback. Chưa có các điều kiện này thì dừng ở bước chuẩn bị, không chuyển sang API bên ngoài.

1. Đã smoke-test G001 (có căn cứ), G075 (thiếu căn cứ) và G088 (ngoài phạm vi); 0/3 request errors.
2. Smoke test cho thấy G001 nêu đúng con số chính nhưng thiếu ngoại lệ học kỳ 3 trong gold answer; cần chấm `answer_complete=false` sau khi reviewer xác nhận. Hai câu từ chối không có citation.
3. Chưa chạy đủ 100 câu tuần tự; runner sẵn sàng ghi latency và response cho từng câu. Backend hiện gọi Qwen một lần mỗi câu sau retrieval.
4. Người chấm hoàn thiện cột đánh giá câu trả lời và từng citation; tính citation accuracy ở cấp citation, tỷ lệ phản hồi có citation đúng, answer correctness/completeness/groundedness, refusal đúng trên hai nhóm unanswerable và false refusal trên nhóm answerable.
5. Nếu đo query rewrite, chạy cùng dataset với rewrite bật/tắt trên cùng corpus/model; báo retrieval và answer-quality riêng. Đây là ablation phụ.

**Đầu ra:** raw response CSV; scored CSV; summary metrics; danh sách lỗi; error analysis theo question ID. Không thay nhãn gold dựa trên câu trả lời chatbot.

### E. Embedding, kết luận reranker và báo cáo

- Giữ MiniLM làm embedding baseline hiện tại; nêu rõ lý do tài nguyên và báo latency/metric hiện có. Kết quả Dense thấp hơn BM25 là dữ liệu để thảo luận giới hạn, không phải bằng chứng MiniLM tốt hơn BGE-M3.
- Chỉ benchmark embedding thứ hai nếu nhóm có thời gian, máy và corpus cố định; đây là thí nghiệm phụ, không thêm model vào sản phẩm mặc định.
- Chốt reranker ngoài scope và giải thích không đủ thời gian/tài nguyên/không phải câu hỏi nghiên cứu.
- Báo các tỷ lệ kèm tử số/mẫu số, `n`, corpus version, model tag, máy chạy, ngày chạy, lỗi và cách chấm. Tách rõ retrieval quality với answer quality.
- Bảng tiến độ chỉ ghi owner/ngày/%/handover khi thành viên xác nhận; evidence là file, log, commit hoặc biên bản có thật.

**Đầu ra cuối:** bảng Research question–baseline–method–metric; Golden Dataset v2 + guideline + cross-review; retrieval/chunking/answer/citation/refusal tables; error analysis; giới hạn; task-owner-evidence; lệnh chạy lại.

## Trình tự khi được duyệt chạy

1. Hoàn thành A và B.
2. Đóng băng dataset/corpus/config; chạy C.
3. Kiểm tra Ollama/embedding local và chạy D smoke test.
4. Chạy D đầy đủ, chấm độc lập.
5. Hoàn thiện E và báo cáo sau khi đã xem lỗi, không viết kết luận trước số liệu.

**Trạng thái hiện tại:** Golden Dataset v2 draft và benchmark retrieval/chunking đã chạy; báo cáo sơ bộ đã xuất. Còn chờ cross-review 100 nhãn, answer-quality benchmark đủ 100 câu, chấm thủ công câu trả lời/citation/refusal và xác minh URL G064. Không có benchmark embedding thứ hai hoặc reranker.

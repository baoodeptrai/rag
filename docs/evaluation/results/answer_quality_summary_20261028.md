# Kết quả đánh giá câu trả lời, citation và refusal

Nguồn chạy: `answer_quality_run_20261028_200546.csv`. Bộ kiểm thử có 60 câu (55 answerable, 5 cần từ chối). Đây là một lần chạy thực tế; các lỗi nhà cung cấp được tính riêng, không xem là câu trả lời đúng.

## Tình trạng chạy

- Lỗi sinh câu trả lời LLM: **42/60 (70.0%)**. Phân loại: HTTP 503: 6, HTTP 429: 27, ConnectionResetError: 1, URLError: 8.
- Câu trả lời nội dung được sinh: **15/55** câu hỏi có căn cứ. Trong đó **14/15** câu trả lời đầy đủ; G022 thiếu các bước 4–6.
- Có chunk bằng chứng chuẩn trong citations retrieval trả về: **44/55 (80.0%)**. Đây là độ phủ retrieval ở cấp câu hỏi, không phải điểm đúng của LLM.

## Citation của câu trả lời đã sinh

- Citation chunk hỗ trợ câu trả lời: **19/20 (95.0%)** trên các citation inline có thể chấm.
- Câu trả lời có toàn bộ citation inline phù hợp: **14/15 (93.3%)**. G003 có một citation không liên quan (chunk trang 18); citation trang 19 có căn cứ cho câu trả lời.
- Các mệnh đề trong câu trả lời đã sinh có căn cứ trong nguồn: **15/15**; tuy nhiên G022 chưa trả lời đủ quy trình.
- Cần phân biệt metadata Chương/Điều: một số trường `article` trong citations retrieval bị lặp sai “Điều 6”. Điểm trên đối chiếu tài liệu/trang/chunk text, không chứng minh metadata Điều đúng.

## Refusal

- Từ chối đúng: **2/5 (40.0%)**. G011 và G012 từ chối đúng; G010, G059, G060 gặp lỗi nhà cung cấp nên không được tính là từ chối đúng.
- Từ chối nhầm câu có căn cứ: **1/55 (1.8%)**; G015 bị từ chối dù sổ tay có thông tin.

## Nhận định

Kết quả hiện tại **chưa đủ để báo cáo như một benchmark chất lượng end-to-end hoàn chỉnh**, vì 42/60 lượt bị lỗi 429/503 hoặc mất kết nối. Citation và groundedness chỉ được chấm cho phản hồi LLM đã sinh; cần chạy lại sau khi xử lý giới hạn/kết nối nhà cung cấp.

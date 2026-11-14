# Kiến trúc offline và việc còn thiếu

## Luồng đích

1. Một model Qwen 4B chạy local thực hiện lượt đầu để phân tích ý định, thực thể và điều kiện cần tìm. Model chỉ chuẩn hóa câu hỏi thành truy vấn ngắn, không trả lời người dùng ở lượt này.
2. BM25 và vector search chạy trên cùng phiên bản chunks đã chuẩn hóa, sau đó hợp nhất bằng RRF. Đầu ra là top-k đoạn nguồn có ID, tài liệu và trang.
3. Bộ kiểm tra bằng chứng áp dụng ngưỡng và yêu cầu đủ mức liên quan. Không đủ căn cứ thì trả lời từ chối có hướng dẫn; không chuyển câu hỏi chung cho LLM để đoán.
4. Cùng model local 4B tổng hợp câu trả lời có trích dẫn từ các đoạn đã lấy. Citation hiển thị phải được dựng từ metadata của retrieval, không tin citation do model tự tạo.

## Trạng thái triển khai

- Đã có: chunking PDF/DOCX, BM25, embedding vector local, Qdrant local, hybrid RRF, cổng bằng chứng sơ bộ, prompt chỉ dùng chunks, citations từ kết quả retrieval.
- Đã thêm hỗ trợ dùng cùng một model qua Ollama OpenAI-compatible local URL cho cả phân tích truy vấn và trả lời; cấu hình `.env` chọn `qwen3:4b`. Máy cần cài Ollama và tải model trước khi chat hoạt động.
- Đã có phát hiện trùng nội dung văn bản chính xác trong lúc ingest; bản lặp bị bỏ qua và được báo trong `duplicates_skipped`. Upload cùng tên thay file raw theo cách nguyên tử.
- Pipeline dựng chunks/BM25/Qdrant ở vùng staging rồi mới thay index active; nếu đọc nguồn hoặc dựng index lỗi thì giữ index hiện tại. Bản index trước nằm trong `.last-good-index` để phục hồi thủ công.
- Chưa có: quản trị trạng thái hiệu lực/ngày hiệu lực/`supersedes` trong UI/API; duyệt và kích hoạt phiên bản tài liệu; truy vấn làm rõ nhiều lượt; ngưỡng retrieval hiệu chuẩn; chấm tự động chất lượng đầu cuối.

Phát hiện trùng hiện tại là so khớp toàn bộ văn bản đã trích xuất sau chuẩn hóa khoảng trắng và chữ hoa/thường. Nó bắt được bản PDF/DOCX trùng phần chữ, nhưng không đủ để nhận ra bản scan, chỉnh sửa nhỏ hay văn bản chỉ trùng một phần. Không tự xóa những trường hợp gần giống vì có thể là bản sửa đổi có hiệu lực khác nhau.

## Vòng đời tài liệu nên có trong sản phẩm

`Tải lên → kiểm tra file/hash → phát hiện trùng → nhập metadata → chờ duyệt → dựng index ứng viên → kiểm tra → kích hoạt phiên bản`.

Metadata tối thiểu: mã văn bản, tên, cơ quan ban hành, loại, số hiệu, phiên bản, ngày ban hành, ngày hiệu lực, ngày hết hiệu lực, `supersedes`, trạng thái (`pending`, `active`, `superseded`, `archived`) và người duyệt. Một checksum trùng hoàn toàn có thể tự bỏ qua; nội dung gần giống phải đưa cho quản trị viên xem. Khi bản mới thay bản cũ, giữ bản cũ trong archive để kiểm toán, nhưng loại nó khỏi index active. Cùng tên tải lên qua API sẽ lưu bản cũ vào `backend/data/archive`; khác tên thì cần quản trị viên chuyển file cũ ra khỏi `raw`.

Index ứng viên được dựng riêng và thay active sau khi toàn bộ file đọc/embedding thành công; lỗi promote sẽ phục hồi bộ active trước đó. Cần bổ sung kiểm tra bộ câu hỏi/citation và manifest hiệu lực trước khi kích hoạt. Giao diện cần phân biệt “đã upload” với “đã được kích hoạt trong chatbot”. Chưa có approval flow hoặc quản lý ngày hiệu lực tự động.

## Số liệu baseline đang có

Kết quả `retrieval_summary.csv` trên 55 câu answerable, top-5: BM25 Recall@5 0.936 / HitRate@5 0.945 / MRR@5 0.787; Dense 0.609 / 0.618 / 0.521; Hybrid RRF 0.755 / 0.764 / 0.616. Trong lần chạy này BM25-only tốt hơn Hybrid; cần phân tích lỗi và kiểm tra cấu hình RRF/corpus trước khi kết luận hybrid có ích. Đây là benchmark retrieval, không phải tỷ lệ trả lời đúng. Báo cáo end-to-end cũ có 42/60 lỗi provider, do đó chưa so sánh được chất lượng model offline.

## Dữ liệu và đánh giá

Repo hiện có `golden_dataset_submission.csv` dùng để **đánh giá**, không phải dataset huấn luyện. Báo cáo retrieval có các baseline BM25-only, Dense-only và Hybrid RRF; báo cáo câu trả lời hiện ghi nhận tỷ lệ lỗi provider cao, nên chưa thể kết luận chất lượng end-to-end. Các nhãn còn cần cross-review. Không gọi đây là dataset training cho đến khi có dữ liệu huấn luyện riêng, quyền sử dụng rõ ràng và quy trình gán nhãn.

Mỗi bản phát hành corpus cần lưu danh sách file nguồn, hash, phiên bản, thời gian hiệu lực và trạng thái thay thế. Khi văn bản mới thay văn bản cũ, quản trị viên phải đánh dấu file cũ hết hiệu lực hoặc xóa khỏi `raw`, rồi dựng lại toàn bộ chunks và chỉ mục; không trộn điều khoản hết hiệu lực vào kết quả. File khác nội dung không được tự động xem là bản thay thế chỉ vì tên giống hoặc khác. Lưu manifest của corpus cùng hash cấu hình chunking/embedding để benchmark có thể tái lập.

## Mẫu câu hỏi và đáp án vàng

Ví dụ dạng câu hỏi cần có trong bộ đánh giá: “Thông báo về thay đổi trên trang sinh viên tác động đến hệ thống thẻ như thế nào?” Mỗi mẫu cần ghi câu hỏi tự nhiên, câu trả lời chuẩn dựa trên tài liệu, đoạn bằng chứng, tài liệu/trang, chunk ID, `answerable`, ngày hiệu lực và người rà soát. Chỉ điền đáp án sau khi xác định đúng văn bản có hiệu lực; ví dụ này hiện là mẫu cấu trúc, chưa phải đáp án đã xác minh.

## Bảng đánh giá bắt buộc trước khi kết luận

| Nhóm đo | Chỉ số cần báo | Baseline/đối chứng |
|---|---|---|
| Retrieval | Recall@5, HitRate@5, MRR@5, median latency; kèm n | BM25-only, Dense-only, Hybrid RRF |
| Trả lời | answer grounded, answer completeness/correctness theo người chấm | cùng model local, so sánh query gốc với query đã phân tích |
| Citation | tài liệu đúng, trang đúng, bằng chứng hỗ trợ câu trả lời | tổng citation được chấm và tỷ lệ câu có citation đúng |
| Từ chối | từ chối đúng trên câu thiếu căn cứ; từ chối nhầm trên câu answerable | tách riêng hai nhóm |
| Điều phối | intent/route accuracy và query rewrite không làm mất điều kiện quan trọng | truy vấn gốc so với truy vấn đã phân tích bằng cùng model Qwen 4B |

Ghi rõ số mẫu, corpus/version, model tag, cấu hình, phần cứng, lỗi/chưa trả lời và quy trình chấm. Tỷ lệ retrieval không được dùng thay cho tỷ lệ trả lời đúng; `confidence_score` hiện tại không phải xác suất đã hiệu chuẩn.

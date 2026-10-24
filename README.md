# UniAssist AI RAG

Dự án được sắp xếp thành hai phần: `frontend/` chứa giao diện React/Vite; `backend/` chứa API FastAPI, pipeline tài liệu và RAG. Các phần TV1–TV3 dùng chung một môi trường Python và một thư mục dữ liệu. Đặt tài liệu PDF/DOCX nguồn vào `backend/data/raw`.

## Cấu trúc

```text
frontend/                 Giao diện React/Vite
backend/
  app/                    API FastAPI và dịch vụ
  rag_project/            Đọc tài liệu, chunking, BM25, Qdrant, hỏi đáp
  data/
    raw/                  PDF/DOCX đầu vào
    processed/            Chunks và chỉ mục BM25
    qdrant/                Vector database local
```

## Chạy Backend và RAG

Sau khi đã có môi trường và tài liệu, có thể khởi động toàn hệ thống từ thư mục gốc bằng một lệnh:

```powershell
.\start.ps1
```

Lần đầu script tự cài các gói còn thiếu. Khi có PDF/DOCX mới hoặc thay đổi trong `backend/data/raw`, script tự dựng lại chỉ mục. Script mở Backend và Frontend trong hai cửa sổ PowerShell riêng.

Để cài đặt thủ công hoặc xử lý lỗi, làm theo các bước dưới đây.

Từ thư mục gốc repository:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Nếu chưa có file `backend/.env`, tạo từ mẫu:

```powershell
Copy-Item .env.example .env
```

Sau đó khởi chạy API:

```powershell
python run.py
```

API chạy ở `http://127.0.0.1:8000`, tài liệu ở `/docs`, trạng thái ở `/health`.

## Thêm tài liệu và lập chỉ mục

Đặt PDF/DOCX được phép sử dụng vào `backend/data/raw`, hoặc tải qua `POST /api/admin/upload`. Sau đó, ở terminal trong thư mục `backend` (đã kích hoạt môi trường Python), chạy:

```powershell
python -m rag_project.pipeline
```

Pipeline tạo chunks, BM25 và Qdrant. Chạy lại sau khi thêm tài liệu để cập nhật chỉ mục. Lần đầu lập chỉ mục cần kết nối mạng để tải embedding model. Hiện chưa có tài liệu nguồn mẫu hợp lệ trong `backend/data/raw`, nên cần thêm tài liệu trước khi hệ thống trả được câu trả lời có trích dẫn.

## Chạy Frontend

Mở terminal mới:

```powershell
cd frontend
npm install
npm run dev
```

Frontend gọi mặc định `http://127.0.0.1:8000/api/chat`. Địa chỉ API và chế độ demo được cấu hình trong `frontend/.env`; mẫu cấu hình ở `frontend/.env.example`. Chế độ demo đang tắt để giao diện gọi Backend thật.

## Cấu hình RAG

Backend đọc `backend/.env`. Có thể cấu hình `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL`, `TOP_K`, `MIN_VECTOR_SIMILARITY`, `MIN_BM25_SCORE` và `RAG_RAW_DIR`. Không đưa khóa API hoặc `.env` lên Git. `confidence_score` là điểm ước lượng retrieval nội bộ, không phải xác suất đúng đã hiệu chuẩn.

`POST /api/chat` nhận `{ "message": "...", "session_id": "..." }`; response gồm câu trả lời, citations thực tế, confidence score và session ID. Nếu chưa có chỉ mục, API báo chưa tìm thấy căn cứ thay vì dùng câu trả lời mẫu. Lịch sử backend lưu trong bộ nhớ tiến trình; lịch sử frontend lưu trong localStorage.

Môi trường cũ được giữ trong `backend/venv-legacy`; tạo môi trường mới theo hướng dẫn ở trên vì virtualenv cũ tham chiếu đường dẫn trước khi sắp xếp lại. File `so_tay_test.pdf` cũ được giữ riêng tại `backend/data/legacy_uploads` và không được đưa vào pipeline tự động.

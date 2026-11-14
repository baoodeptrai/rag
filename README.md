# UniAssist AI RAG

Trợ lý hỏi đáp dành cho sinh viên, dùng tài liệu PDF/DOCX làm nguồn. Frontend React/Vite gọi API FastAPI; backend kết hợp tìm kiếm BM25 và vector Qdrant, rồi dùng Ollama chạy mô hình ngôn ngữ local để tạo câu trả lời có trích dẫn.

## Yêu cầu

- Windows 10/11 và PowerShell (có thể chạy thủ công trên hệ điều hành khác; các script `.ps1` chỉ dành cho PowerShell).
- Python 3.11 trở lên.
- Node.js tương thích Vite 8 (khuyến nghị Node.js 22.12 trở lên) và npm.
- Ollama để chat bằng mô hình local. Cần tải model trước khi chạy lần đầu; xem [Cấu hình Ollama](#cấu-hình-ollama).
- Tài liệu PDF/DOCX được phép sử dụng, nếu muốn chatbot trả lời theo kho tài liệu riêng.

## Khởi chạy nhanh trên Windows

Mở PowerShell tại thư mục gốc của project và chạy:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\start.ps1
```

Lần chạy đầu, script tạo `backend/.venv`, cài Python packages và frontend packages, lập chỉ mục tài liệu mới trong `backend/data/raw`, sau đó mở API và giao diện trong hai cửa sổ PowerShell. Sau đó truy cập:

- Giao diện: <http://localhost:5173>
- API và Swagger: <http://127.0.0.1:8000/docs>
- Trạng thái API: <http://127.0.0.1:8000/health>

Để dừng ứng dụng, đóng hai cửa sổ server đã mở. Chạy lại `start.ps1` sau khi thêm hoặc sửa tài liệu; script so sánh nội dung tài liệu với manifest để quyết định có lập chỉ mục lại hay không.

## Cài đặt và chạy thủ công

### 1. Cấu hình Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Mở `backend/.env`, đặt `ADMIN_API_TOKEN` thành một chuỗi bí mật riêng. Có thể giữ các thiết lập local mặc định nếu API chạy ở cổng 8000. Không chia sẻ file `.env` hoặc commit file này lên Git.

### 2. Cấu hình Ollama

Cài Ollama, khởi động Ollama và tải model được cấu hình trong `backend/.env` (mặc định `qwen3:4b`):

```powershell
ollama pull qwen3:4b
```

Backend dùng Ollama local tại `http://127.0.0.1:11434`. Phần embedding sử dụng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; hãy đảm bảo model này đã được tải/cache trên máy trước khi chạy pipeline hoặc truy vấn lần đầu. Sau khi đã có model trong cache, quá trình inference được cấu hình chạy offline. Nếu thay `LLM_MODEL` hoặc `EMBEDDING_MODEL`, tải/cache model tương ứng trước.

### 3. Thêm tài liệu và lập chỉ mục

Chép PDF/DOCX vào `backend/data/raw`. Giới hạn upload mặc định là 20 MB mỗi file; chỉ PDF và DOCX được chấp nhận. Từ thư mục `backend`, chạy:

```powershell
python -m rag_project.pipeline
```

Pipeline đọc toàn bộ tài liệu trong `data/raw`, tạo chunks và chỉ mục BM25 trong `data/processed`, đồng thời lưu vector database ở `data/qdrant`. Chỉ mục mới được đưa vào sử dụng sau khi pipeline chạy thành công. Lỗi đọc tài liệu hoặc lỗi tạo index sẽ khiến index hiện tại được giữ lại. Khi kho tài liệu trống và pipeline chạy thành công, index cũ được dọn.

`start.ps1` tự kiểm tra thay đổi tài liệu và gọi pipeline khi cần. Khi chạy backend thủ công, hãy tự chạy lại lệnh pipeline sau mỗi lần thay đổi kho tài liệu.

### 4. Khởi chạy API và giao diện

Trong terminal thứ nhất, từ `backend/` và đã kích hoạt virtualenv:

```powershell
python run.py
```

Trong terminal thứ hai:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Mặc định giao diện ở <http://localhost:5173> và gọi API tại `http://127.0.0.1:8000`. Có thể đổi địa chỉ bằng `VITE_API_BASE_URL` trong `frontend/.env`. `VITE_DEMO_MODE=false` gọi backend thật; đặt `true` chỉ để xem phản hồi demo, không dùng dữ liệu RAG thật.

## Quản lý tài liệu

Trong giao diện, mở **Quản lý tài liệu** và nhập giá trị `ADMIN_API_TOKEN` từ `backend/.env`. Quản trị viên có thể tải tài liệu lên, xem tài liệu hiện hành/lưu trữ và cập nhật chỉ mục. Các endpoint quản trị yêu cầu token; không đặt token trong frontend hoặc đưa token vào tài liệu công khai.

- **Thêm tài liệu:** tải file mới lên kho rồi cập nhật chỉ mục.
- **Thay tài liệu:** chọn bản hiện hành cần thay; bản cũ được lưu trữ và bản mới trở thành bản active.
- **Tài liệu sửa đổi/phụ lục:** lưu thành file riêng và liên kết với tài liệu gốc khi phù hợp.

Chỉ tài liệu active được đưa vào index. Có thể đặt nguồn tài liệu ở vị trí khác bằng `RAG_RAW_DIR` trong `backend/.env`. Không xóa tài liệu lưu trữ cho đến khi index mới được dựng thành công và citation đã được rà soát.

## Cấu hình thường dùng

| Biến | File | Ý nghĩa |
|---|---|---|
| `HOST`, `PORT`, `DEBUG` | `backend/.env` | Địa chỉ bind, cổng API (mặc định 8000) và tự reload khi phát triển |
| `BACKEND_CORS_ORIGINS` | `backend/.env` | Các origin frontend được phép gọi API |
| `RAG_RAW_DIR` | `backend/.env` | Thư mục tài liệu nguồn; mặc định `backend/data/raw` |
| `MAX_FILE_SIZE_MB`, `ALLOWED_EXTENSIONS` | `backend/.env` | Giới hạn upload và loại file được nhận |
| `EMBEDDING_MODEL`, `TOP_K` | `backend/.env` | Model embedding và số đoạn truy xuất |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_TIMEOUT` | `backend/.env` | Địa chỉ Ollama local, model chat và timeout |
| `ADMIN_API_TOKEN` | `backend/.env` | Token bảo vệ API quản trị tài liệu |
| `VITE_API_BASE_URL` | `frontend/.env` | Địa chỉ backend mà frontend gọi |
| `VITE_DEMO_MODE` | `frontend/.env` | Bật/tắt dữ liệu demo; để `false` khi dùng RAG thật |

Giữ Ollama ở địa chỉ loopback (`localhost` hoặc `127.0.0.1`); backend từ chối endpoint LLM ngoài máy local. Khi đổi model embedding, cần chạy lại pipeline để tái tạo vector index bằng model đó.

## Kiểm tra nhanh và xử lý lỗi

- **Không tìm thấy Python/npm:** cài Python 3.11+ và Node.js, mở lại terminal rồi chạy `start.ps1`.
- **Không chạy được script PowerShell:** chạy `Set-ExecutionPolicy -Scope Process Bypass` trong terminal hiện tại.
- **Cổng 8000 hoặc 5173 đã được dùng:** dừng tiến trình đang chiếm cổng hoặc đổi cấu hình cổng tương ứng; cập nhật `VITE_API_BASE_URL` nếu API đổi cổng.
- **Chat báo Ollama/model chưa sẵn sàng:** kiểm tra Ollama đang chạy, `LLM_MODEL` có tồn tại (`ollama list`) và tải model bằng `ollama pull <tên-model>`.
- **Lỗi embedding/offline:** tải model embedding khi máy có mạng; backend chủ động bật chế độ chỉ dùng model đã cache.
- **Không tìm thấy căn cứ:** kiểm tra file trong `backend/data/raw`, định dạng PDF/DOCX và chạy lại `python -m rag_project.pipeline` từ `backend/`.
- **Không truy cập được trang quản trị:** kiểm tra `ADMIN_API_TOKEN` trong `backend/.env` và nhập đúng token trên giao diện.

## Cấu trúc thư mục

```text
frontend/                 React, Vite và giao diện chat/quản trị
backend/app/              FastAPI, API chat, upload và quản trị tài liệu
backend/rag_project/      Trích xuất, chia chunks, lập chỉ mục và truy xuất RAG
backend/data/raw/         Tài liệu nguồn PDF/DOCX
backend/data/processed/   Chunks, chỉ mục BM25 và manifest
backend/data/qdrant/      Vector database local (được tạo khi lập chỉ mục)
docs/evaluation/          Kế hoạch và kết quả đánh giá offline
start.ps1                 Cài phần thiếu, kiểm tra index, mở API và frontend
```

## API và đánh giá

- Chat: `POST /api/chat`, body gồm `message` và `session_id` (session ID có thể bỏ trống để tạo phiên mới). Câu trả lời trả về citations, confidence score và session ID.
- Health: `GET /health`.
- Tài liệu API đầy đủ: <http://127.0.0.1:8000/docs>.
- Kết quả benchmark, hướng dẫn và giới hạn đánh giá: [`docs/evaluation/README.md`](docs/evaluation/README.md).

Chat chỉ dựa trên các đoạn được truy xuất; nếu không tìm được căn cứ phù hợp, hệ thống trả lời rằng tài liệu hiện có chưa cung cấp thông tin. `confidence_score` là điểm retrieval nội bộ, không phải xác suất câu trả lời đúng đã hiệu chuẩn. Lịch sử phiên backend lưu trong bộ nhớ tiến trình; frontend lưu lịch sử trên trình duyệt.

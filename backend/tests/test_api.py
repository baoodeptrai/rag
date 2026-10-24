"""
Module: tests.test_api
Mô tả: Bộ kiểm thử tự động (Unit / Integration Tests) cho Backend API của TV3.
Dành cho TV3 tự kiểm tra trước khi bàn giao và làm nền tảng cho TV5 (Tester).
Chạy kiểm thử bằng lệnh: pytest -v
"""

import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_01_health_check():
    """Kiểm tra GET /health trả về 200 OK và trạng thái healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["service"] == "student-rag-backend-api"


def test_02_health_check_via_api():
    """Kiểm tra GET /api/health cũng trả về 200 OK."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_03_chat_valid_question():
    """Kiểm tra POST /api/chat với câu hỏi hợp lệ."""
    payload = {
        "message": "Điều kiện để xét học bổng khuyến khích là gì?",
        "session_id": "test_session_123"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Kiểm tra đúng Schema thống nhất (Bước 23)
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert "citations" in data
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) > 0
    
    # Kiểm tra cấu trúc citation
    cit = data["citations"][0]
    assert "doc_name" in cit
    assert "page_number" in cit
    assert "chapter" in cit
    assert "article" in cit
    assert data["session_id"] == "test_session_123"


def test_04_chat_empty_whitespace_message():
    """Kiểm tra POST /api/chat với câu hỏi chỉ có khoảng trắng (Bước 21 - phải chặn)."""
    payload = {
        "message": "    ",
        "session_id": "test_session_123"
    }
    response = client.post("/api/chat", json=payload)
    # Pydantic validator ném ValueError sẽ trả về 422 kèm message thân thiện
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "không được để trống" in data["message"]


def test_05_chat_missing_body():
    """Kiểm tra POST /api/chat với JSON rỗng {}."""
    response = client.post("/api/chat", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False


def test_06_chat_history():
    """Kiểm tra lưu vết và lấy lại lịch sử chat (Bước 25)."""
    session_id = "test_history_session_999"
    # Gửi câu hỏi
    client.post("/api/chat", json={"message": "Quy chế tín chỉ", "session_id": session_id})
    
    # Lấy lịch sử
    response = client.get(f"/api/chat/history/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["total_messages"] >= 2  # 1 user + 1 assistant
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"


def test_07_admin_upload_valid_pdf():
    """Kiểm tra tải lên file PDF hợp lệ (Bước 26)."""
    file_content = b"%PDF-1.4 Fake test PDF content for graduation project"
    files = {
        "file": ("so_tay_test.pdf", io.BytesIO(file_content), "application/pdf")
    }
    data = {"category": "dao_tao"}
    response = client.post("/api/admin/upload", files=files, data=data)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert "so_tay_test.pdf" in res_json["file_name"]
    assert res_json["category"] == "dao_tao"


def test_08_admin_upload_invalid_extension():
    """Kiểm tra chặn file nguy hiểm / không đúng định dạng (.exe, .txt)."""
    file_content = b"echo 'hack'"
    files = {
        "file": ("virus.exe", io.BytesIO(file_content), "application/octet-stream")
    }
    response = client.post("/api/admin/upload", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "không được hỗ trợ" in data["message"]


def test_09_chat_invalid_json_type():
    """Kiểm tra JSON sai kiểu dữ liệu (Điều kiện tự kiểm tra: 'JSON sai')."""
    # Gửi JSON không hợp lệ: message là list hoặc number thay vì chuỗi
    response = client.post("/api/chat", json={"message": 123456})
    # Pydantic tự động convert số thành chuỗi nếu được, thử gửi object phức tạp
    response_invalid = client.post("/api/chat", json={"message": {"invalid": "object"}})
    assert response_invalid.status_code == 422
    data = response_invalid.json()
    assert data["success"] is False
    assert "VALIDATION_ERROR" in data["error_code"]


def test_10_chat_rag_error_handling(monkeypatch):
    """
    Kiểm tra xử lý lỗi RAG (Điều kiện tự kiểm tra: 'lỗi RAG đều được xử lý rõ ràng').
    Đảm bảo:
    - Trả mã HTTP phù hợp (500).
    - Không trả stack trace hoặc khóa API về client (Bước 24).
    """
    from app.services.rag_service import rag_service

    def mock_ask_fail(query, session_id):
        raise RuntimeError("OpenAI API Connection Timeout: sk-secret-fake-key-12345")

    # Giả lập RAG gặp sự cố
    monkeypatch.setattr(rag_service, "_call_tv2_ask_rag_engine", mock_ask_fail)

    response = client.post("/api/chat", json={"message": "Hỏi về quy chế"})
    assert response.status_code == 500
    data = response.json()
    assert data["success"] is False
    # Tuyệt đối không để lộ key OpenAI hoặc stack trace
    assert "sk-secret-fake-key-12345" not in response.text
    assert "Traceback" not in response.text
    assert "RAG_SERVICE_ERROR" in data["error_code"]


def test_11_cors_preflight():
    """Kiểm tra cấu hình CORS cho Frontend dev (Bước 27)."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/chat", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


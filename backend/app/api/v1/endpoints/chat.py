from fastapi import APIRouter, status, Depends
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryResponse
from app.services.rag_service import rag_service, RAGService
from app.services.session_service import session_service, SessionService

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Gửi câu hỏi tới Trợ lý ảo AI",
    description="Truy vấn RAG để trả lời câu hỏi và trả về danh sách trích dẫn nguồn."
)
async def chat_with_assistant(
    request: ChatRequest,
    rag_svc: RAGService = Depends(lambda: rag_service),
    sess_svc: SessionService = Depends(lambda: session_service)
):
    active_session_id = sess_svc.get_or_create_session_id(request.session_id)
    sess_svc.add_user_message(active_session_id, request.message)

    rag_result = rag_svc.ask(query=request.message, session_id=active_session_id)

    sess_svc.add_assistant_message(
        session_id=active_session_id,
        content=rag_result["answer"],
        citations=rag_result["citations"]
    )

    return ChatResponse(
        answer=rag_result["answer"],
        citations=rag_result["citations"],
        confidence_score=rag_result["confidence_score"],
        session_id=active_session_id
    )


@router.get(
    "/chat/history/{session_id}",
    response_model=ChatHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem lịch sử trò chuyện theo session_id"
)
async def get_chat_history(
    session_id: str,
    sess_svc: SessionService = Depends(lambda: session_service)
):
    return sess_svc.get_history(session_id)

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";
function firstDefined(...values) {
  return values.find((value) => value !== undefined && value !== null && value !== "");
}

function normalizeCitation(item, index) {
  if (!item || typeof item !== "object") return null;

  const docName = firstDefined(
    item.doc_name, item.document_name, item.document, item.filename,
    item.source_name, item.title, item.name
  );
  const url = firstDefined(item.url, item.document_url, item.file_url, item.source_url);
  const page = firstDefined(item.page_number, item.page, item.page_no);
  const chapter = firstDefined(item.chapter, item.chapter_name);
  const article = firstDefined(item.article, item.article_name, item.section);
  const clause = firstDefined(item.clause, item.clause_name);

  // Do not fabricate a document name or URL if the API did not provide one.
  if (!docName && !url && page == null && !chapter && !article) return null;

  return {
    id: firstDefined(item.id, item.chunk_id, `${docName || "source"}-${index}`),
    doc_name: docName || "Tài liệu tham khảo",
    url: typeof url === "string" ? url : null,
    page_number: page ?? null,
    chapter: chapter ?? null,
    article: article ?? null,
    clause: clause ?? null,
    excerpt: firstDefined(item.excerpt, item.snippet, item.content, item.text) || null,
  };
}

export function normalizeChatResponse(data) {
  if (!data || typeof data !== "object") {
    throw new Error("Backend trả về dữ liệu không đúng định dạng.");
  }

  const answer = firstDefined(
    data.answer, data.response, data.reply, data.message,
    data.result?.answer, data.data?.answer, data.data?.response
  );

  if (typeof answer !== "string" || !answer.trim()) {
    throw new Error("Phản hồi Backend chưa có trường câu trả lời hợp lệ. Cần đối chiếu cấu trúc API với nhóm Backend.");
  }

  const rawSources = firstDefined(
    data.citations, data.sources, data.references, data.documents,
    data.result?.citations, data.result?.sources,
    data.data?.citations, data.data?.sources
  );

  return {
    answer: answer.trim(),
    citations: Array.isArray(rawSources)
      ? rawSources.map(normalizeCitation).filter(Boolean)
      : [],
    insufficientEvidence: Boolean(
      data.insufficient_evidence ?? data.no_evidence ?? data.result?.insufficient_evidence
    ),
    raw: data,
  };
}

export async function sendChatMessage({ message, sessionId, signal }) {
  if (DEMO_MODE) {
    await new Promise((resolve) => setTimeout(resolve, 700));
    return {
      answer: "Đây là chế độ demo của Frontend. Chưa có câu trả lời nào được truy xuất từ tài liệu thật. Khi Backend RAG sẵn sàng, hãy đặt VITE_DEMO_MODE=false và cấu hình đúng API.",
      citations: [],
      insufficientEvidence: true,
      demo: true,
    };
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) {
      throw new DOMException("Yêu cầu đã bị hủy.", "AbortError");
    }
    throw new Error(`Không kết nối được Backend tại ${API_BASE_URL}. Hãy kiểm tra Backend và cấu hình API URL.`, { cause: error });
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object"
      ? firstDefined(payload.detail, payload.message, payload.error)
      : payload;
    throw new Error(`Backend trả về lỗi HTTP ${response.status}${detail ? `: ${detail}` : ""}`);
  }

  if (typeof payload === "string") {
    throw new Error("Backend không trả về JSON. Cần kiểm tra định dạng phản hồi API.");
  }

  return { ...normalizeChatResponse(payload), demo: false };
}

export function isDemoMode() {
  return DEMO_MODE;
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

import CitationList from "./CitationList";

export default function MessageItem({ message }) {
  const role = message.role === "error" ? "error" : message.role;

  return (
    <article className={`message message-${role}`} aria-live={role === "error" ? "assertive" : "off"}>
      {message.role !== "user" && <div className="message-avatar">{role === "error" ? "!" : "U"}</div>}
      <div className="message-body">
        {message.role !== "user" && (
          <div className="message-author">{role === "error" ? "Thông báo lỗi" : "UniAssist AI"}</div>
        )}
        <div className="message-text">{message.text}</div>
        {message.insufficientEvidence && (
          <p className="evidence-notice">Chưa có đủ bằng chứng từ tài liệu để xác nhận câu trả lời.</p>
        )}
        {message.citations?.length > 0 && <CitationList citations={message.citations} />}
      </div>
    </article>
  );
}

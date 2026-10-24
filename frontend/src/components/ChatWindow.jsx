import MessageItem from "./MessageItem";
import LoadingIndicator from "./LoadingIndicator";
import ChatInput from "./ChatInput";

const suggestions = [
  "Điều kiện đăng ký tín chỉ là gì?",
  "Quy định về học phí như thế nào?",
  "Điều kiện xét tốt nghiệp gồm những gì?",
  "Sinh viên cần làm gì khi bị cảnh báo học tập?",
];

export default function ChatWindow({ messages, input, setInput, loading, onSend, onSubmit }) {
  return (
    <>
      <section className="chat-content">
        {messages.length <= 1 && (
          <div className="welcome-section">
            <div className="welcome-icon">✳</div>
            <div className="eyebrow">ĐỒNG HÀNH CÙNG SINH VIÊN</div>
            <h2>Hôm nay bạn cần hỗ trợ gì?</h2>
            <p>Đặt câu hỏi về quy chế, học phí, tín chỉ và hướng dẫn sinh viên.</p>
            <div className="suggestion-grid">
              {suggestions.map((suggestion) => (
                <button className="suggestion-card" key={suggestion} onClick={() => onSend(suggestion)} disabled={loading}>
                  <span>{suggestion}</span><span className="suggestion-arrow">↗</span>
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="message-list">
          {messages.map((message) => <MessageItem message={message} key={message.id} />)}
          {loading && <LoadingIndicator />}
        </div>
      </section>
      <footer className="composer-area">
        <ChatInput value={input} onChange={setInput} onSubmit={onSubmit} loading={loading} />
        <p className="disclaimer">Không chia sẻ thông tin nhạy cảm. Câu trả lời cần được đối chiếu với tài liệu chính thức.</p>
      </footer>
    </>
  );
}

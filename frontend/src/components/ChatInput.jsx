export default function ChatInput({ value, onChange, onSubmit, loading }) {
  return (
    <form className="composer" onSubmit={onSubmit}>
      <label className="visually-hidden" htmlFor="chat-question">Câu hỏi của bạn</label>
      <textarea
        id="chat-question"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            onSubmit(event);
          }
        }}
        placeholder="Nhập câu hỏi của bạn..."
        rows={2}
        maxLength={2000}
        disabled={loading}
      />
      <div className="composer-bottom">
        <span className="composer-hint">Enter để gửi · Shift + Enter để xuống dòng · Tối đa 2.000 ký tự</span>
        <button className="send-button" type="submit" disabled={!value.trim() || loading} aria-label="Gửi câu hỏi">
          ↑
        </button>
      </div>
    </form>
  );
}

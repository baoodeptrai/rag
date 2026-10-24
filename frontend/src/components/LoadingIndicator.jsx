export default function LoadingIndicator() {
  return (
    <div className="loading-row" role="status" aria-live="polite">
      <div className="message-avatar">U</div>
      <div className="loading-bubble">
        <span /><span /><span />
        <small>Đang xử lý câu hỏi...</small>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useRef, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import AdminDocuments from "./components/AdminDocuments";
import { getApiBaseUrl, isDemoMode, sendChatMessage } from "./services/chatService";
import "./App.css";

const STORAGE_KEY = "uniassist-conversations-v1";

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function createConversation() {
  return {
    id: makeId(),
    title: "Cuộc trò chuyện mới",
    messages: [],
    updatedAt: Date.now(),
  };
}

function loadConversations() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return null;
    const parsed = JSON.parse(saved);
    if (!Array.isArray(parsed) || parsed.length === 0) return null;
    return parsed.filter((item) =>
      item && typeof item.id === "string" && Array.isArray(item.messages)
    );
  } catch {
    return null;
  }
}

function App() {
  const [conversations, setConversations] = useState(() => loadConversations() || [createConversation()]);
  const [activeConversationId, setActiveConversationId] = useState(() => {
    const saved = loadConversations();
    return saved?.[0]?.id || null;
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("chat");
  const [notice, setNotice] = useState("");
  const abortRef = useRef(null);

  const activeConversation = useMemo(
    () => conversations.find((item) => item.id === activeConversationId) || conversations[0],
    [conversations, activeConversationId]
  );
  const messages = activeConversation?.messages || [];

  useEffect(() => {
    if (!activeConversationId && conversations[0]) setActiveConversationId(conversations[0].id);
  }, [activeConversationId, conversations]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch {
      setNotice("Không thể lưu lịch sử vào trình duyệt. Bạn vẫn có thể tiếp tục sử dụng phiên hiện tại.");
    }
  }, [conversations]);

  useEffect(() => () => abortRef.current?.abort(), []);

  function updateConversation(id, updater) {
    setConversations((old) => old.map((conversation) =>
      conversation.id === id ? updater(conversation) : conversation
    ));
  }

  function newConversation() {
    abortRef.current?.abort();
    const conversation = createConversation();
    setConversations((old) => [conversation, ...old]);
    setActiveConversationId(conversation.id);
    setInput("");
    setLoading(false);
    setNotice("");
    setActiveTab("chat");
  }

  function chooseConversation(conversation) {
    abortRef.current?.abort();
    setActiveConversationId(conversation.id);
    setInput("");
    setLoading(false);
    setNotice("");
    setActiveTab("chat");
  }

  function deleteConversation(id) {
    abortRef.current?.abort();
    setConversations((old) => {
      const remaining = old.filter((item) => item.id !== id);
      return remaining.length ? remaining : [createConversation()];
    });

    if (activeConversationId === id) {
      const remaining = conversations.filter((item) => item.id !== id);
      setActiveConversationId(remaining[0]?.id || null);
      setInput("");
      setLoading(false);
    }
    setNotice("Đã xóa hội thoại khỏi lịch sử lưu trên trình duyệt. Dữ liệu trên máy chủ (nếu có) không bị xóa.");
  }

  async function sendMessage(value = input) {
    const question = value.trim();
    if (!question || loading || !activeConversation) return;

    const conversationId = activeConversation.id;
    const userMessage = {
      id: makeId(),
      role: "user",
      text: question,
      citations: [],
      createdAt: Date.now(),
    };

    updateConversation(conversationId, (conversation) => ({
      ...conversation,
      title: conversation.title === "Cuộc trò chuyện mới"
        ? question.slice(0, 42) + (question.length > 42 ? "…" : "")
        : conversation.title,
      messages: [...conversation.messages, userMessage],
      updatedAt: Date.now(),
    }));
    setInput("");
    setLoading(true);
    setNotice("");

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const result = await sendChatMessage({
        message: question,
        sessionId: conversationId,
        signal: controller.signal,
      });

      const answerMessage = {
        id: makeId(),
        role: "assistant",
        text: result.answer,
        citations: result.citations || [],
        insufficientEvidence: result.insufficientEvidence,
        demo: result.demo,
        createdAt: Date.now(),
      };
      updateConversation(conversationId, (conversation) => ({
        ...conversation,
        messages: [...conversation.messages, answerMessage],
        updatedAt: Date.now(),
      }));
    } catch (error) {
      if (error.name !== "AbortError") {
        updateConversation(conversationId, (conversation) => ({
          ...conversation,
          messages: [...conversation.messages, {
            id: makeId(),
            role: "error",
            text: error.message || "Đã xảy ra lỗi không xác định. Vui lòng thử lại.",
            citations: [],
            createdAt: Date.now(),
          }],
          updatedAt: Date.now(),
        }));
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage();
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">U</div>
          <div>
            <div className="brand-name">UniAssist</div>
            <div className="brand-caption">STUDENT AI ASSISTANT</div>
          </div>
        </div>

        <button className="new-chat-button" onClick={newConversation}>
          <span>＋</span> Cuộc trò chuyện mới
        </button>

        <div className="sidebar-label">KHÔNG GIAN LÀM VIỆC</div>
        <button className={`nav-item ${activeTab === "chat" ? "selected" : ""}`} onClick={() => setActiveTab("chat")}>
          <span>▤</span> Trợ lý sinh viên
        </button>
        <button className={`nav-item ${activeTab === "admin" ? "selected" : ""}`} onClick={() => setActiveTab("admin")}>
          <span>⚙</span> Quản lý tài liệu
        </button>

        <div className="sidebar-label history-label">GẦN ĐÂY</div>
        <div className="conversation-list">
          {conversations.map((conversation) => (
            <div className={`conversation-row ${activeConversationId === conversation.id ? "current" : ""}`} key={conversation.id}>
              <button className="conversation-button" onClick={() => chooseConversation(conversation)} title={conversation.title}>
                <span>◷</span><span className="conversation-title">{conversation.title}</span>
              </button>
              <button className="delete-conversation" title="Xóa khỏi lịch sử trình duyệt" aria-label={`Xóa ${conversation.title}`} onClick={() => deleteConversation(conversation.id)}>×</button>
            </div>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="avatar">SV</div>
          <div className="profile-text"><strong>Sinh viên</strong><span>UniAssist AI</span></div>
          <span className="profile-more">⋯</span>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <div className="breadcrumb">Không gian học tập / {activeTab === "admin" ? "Quản trị" : "Trợ lý AI"}</div>
            <h1>{activeTab === "admin" ? "Quản lý tài liệu" : "Trợ lý sinh viên"}</h1>
          </div>
          <div className="connection-status">
            <span className={`status-dot ${isDemoMode() ? "demo-dot" : "api-dot"}`} />
            {isDemoMode() ? "Chế độ demo" : `API: ${getApiBaseUrl()}`}
          </div>
        </header>

        {notice && <div className="app-notice" role="status">{notice}<button onClick={() => setNotice("")} aria-label="Đóng thông báo">×</button></div>}

        {activeTab === "admin" ? (
          <AdminDocuments />
        ) : (
          <ChatWindow
            messages={messages}
            input={input}
            setInput={setInput}
            loading={loading}
            onSend={sendMessage}
            onSubmit={handleSubmit}
          />
        )}
      </main>
    </div>
  );
}

export default App;

import { useEffect, useMemo, useState } from "react";
import { getAdminDocuments, reindexAdminDocuments, uploadAdminDocument } from "../services/adminService";

const TOKEN_KEY = "uniassist-admin-token";
const formatSize = (size) => size < 1024 * 1024 ? `${(size / 1024).toFixed(0)} KB` : `${(size / (1024 * 1024)).toFixed(1)} MB`;

export default function AdminDocuments() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || "");
  const [tokenInput, setTokenInput] = useState("");
  const [documents, setDocuments] = useState([]);
  const [archive, setArchive] = useState([]);
  const [changeType, setChangeType] = useState("new");
  const [related, setRelated] = useState("");
  const [category, setCategory] = useState("dao_tao");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const activeDocs = useMemo(() => documents.filter((doc) => doc.status === "active"), [documents]);
  const pendingCount = activeDocs.filter((doc) => doc.index_status === "pending").length;

  async function refreshDocs(accessToken = token) {
    const result = await getAdminDocuments(accessToken);
    setDocuments(result.documents || []);
    setArchive(result.archive || []);
  }

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    async function loadDocuments() {
      try {
        const result = await getAdminDocuments(token);
        if (!cancelled) {
          setDocuments(result.documents || []);
          setArchive(result.archive || []);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err.message);
        if (/401|403/.test(err.message)) {
          sessionStorage.removeItem(TOKEN_KEY);
          setToken("");
        }
      }
    }
    loadDocuments();
    return () => { cancelled = true; };
  }, [token]);

  async function unlock(event) {
    event.preventDefault();
    setError("");
    try {
      await refreshDocs(tokenInput);
      sessionStorage.setItem(TOKEN_KEY, tokenInput);
      setToken(tokenInput);
      setTokenInput("");
    } catch (err) {
      setError(err.message);
    }
  }

  function signOut() {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken("");
    setDocuments([]);
    setArchive([]);
    setError("");
    setNotice("");
  }

  async function handleUpload(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    if (!file) return setError("Chọn file PDF hoặc Word trước khi tải lên.");
    if (changeType === "replace" && !related) return setError("Chọn tài liệu cũ cần thay thế.");
    setBusy(true);
    setError("");
    setNotice("");
    const form = new FormData();
    form.append("file", file);
    form.append("category", category);
    form.append("change_type", changeType);
    if (related) form.append("related_document", related);
    try {
      const result = await uploadAdminDocument(token, form);
      setNotice(`${result.file_name} đã được tải lên. Hãy cập nhật chỉ mục để chatbot dùng nội dung mới.`);
      setFile(null);
      formElement.reset();
      await refreshDocs();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleReindex() {
    setBusy(true);
    setError("");
    setNotice("Đang dựng lại chỉ mục từ tài liệu hiện hành. Quá trình này có thể mất vài phút.");
    try {
      const result = await reindexAdminDocuments(token);
      setNotice(result.message);
      await refreshDocs();
    } catch (err) {
      setError(err.message);
      setNotice("");
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <section className="admin-page">
        <div className="admin-lock-card">
          <div className="admin-icon">♙</div>
          <h2>Khu vực quản trị tài liệu</h2>
          <p>Chỉ người được giao quản lý tài liệu mới có quyền thêm, thay thế và cập nhật chỉ mục.</p>
          <form onSubmit={unlock} className="admin-login-form">
            <label htmlFor="admin-token">Mã quản trị</label>
            <input id="admin-token" type="password" autoComplete="current-password" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} placeholder="Nhập ADMIN_API_TOKEN" required />
            <button className="primary-button" type="submit">Mở quản trị</button>
          </form>
          <small>Mã được cấu hình bởi quản trị viên trong <code>backend/.env</code>.</small>
          {error && <div className="admin-alert error">{error}</div>}
        </div>
      </section>
    );
  }

  return (
    <section className="admin-page">
      <div className="admin-title-row">
        <div><span className="admin-eyebrow">QUẢN TRỊ NỘI DUNG</span><h2>Quản lý tài liệu</h2><p>Tải tài liệu, chọn cách cập nhật và dựng lại chỉ mục cho chatbot.</p></div>
        <button className="secondary-button" type="button" onClick={signOut}>Đăng xuất quản trị</button>
      </div>

      {error && <div className="admin-alert error">{error}</div>}
      {notice && <div className="admin-alert success">{notice}</div>}

      <div className="admin-grid">
        <form className="admin-card admin-upload-card" onSubmit={handleUpload}>
          <h3>Tải tài liệu lên</h3>
          <label htmlFor="change-type">Cách cập nhật</label>
          <select id="change-type" value={changeType} onChange={(e) => { setChangeType(e.target.value); setRelated(""); }}>
            <option value="new">Thêm tài liệu mới</option>
            <option value="replace">Thay thế toàn bộ bản cũ</option>
            <option value="amendment">Thêm văn bản sửa đổi / phụ lục</option>
          </select>
          {(changeType === "replace" || changeType === "amendment") && (
            <>
              <label htmlFor="related-document">{changeType === "replace" ? "Bản hiện hành cần thay thế" : "Văn bản gốc liên quan (không bắt buộc)"}</label>
              <select id="related-document" value={related} onChange={(e) => setRelated(e.target.value)} required={changeType === "replace"}>
                <option value="">{changeType === "replace" ? "Chọn tài liệu" : "Không chọn"}</option>
                {activeDocs.map((doc) => <option key={doc.file_name} value={doc.file_name}>{doc.file_name}</option>)}
              </select>
            </>
          )}
          <label htmlFor="doc-category">Nhóm tài liệu</label>
          <select id="doc-category" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="dao_tao">Đào tạo</option><option value="cong_tac_sinh_vien">Công tác sinh viên</option><option value="hoc_phi_hoc_bong">Học phí, học bổng</option><option value="khac">Khác</option>
          </select>
          <label htmlFor="document-file">File PDF hoặc Word</label>
          <input id="document-file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
          <div className="admin-help">
            {changeType === "new" && "Tài liệu độc lập sẽ được thêm vào kho hiện hành."}
            {changeType === "replace" && "Bản cũ sẽ được lưu trong kho lưu trữ; chỉ bản mới được lập chỉ mục."}
            {changeType === "amendment" && "Giữ nguyên tài liệu gốc và thêm văn bản sửa đổi/phụ lục làm nguồn riêng."}
          </div>
          <button className="primary-button" type="submit" disabled={busy}>{busy ? "Đang xử lý…" : "Tải tài liệu lên"}</button>
        </form>

        <div className="admin-card">
          <div className="admin-list-heading"><div><h3>Tài liệu đang dùng</h3><p>{activeDocs.length} tài liệu</p></div><button className="primary-button" type="button" onClick={handleReindex} disabled={busy || activeDocs.length === 0}>{busy ? "Đang cập nhật…" : pendingCount ? `Cập nhật chỉ mục (${pendingCount})` : "Dựng lại chỉ mục"}</button></div>
          <div className="admin-document-list">
            {activeDocs.length === 0 && <div className="admin-empty">Chưa có tài liệu trong kho.</div>}
            {activeDocs.map((doc) => <article className="admin-document-row" key={doc.file_name}><span className="document-file-icon">▤</span><div className="document-details"><strong>{doc.file_name}</strong><span>{formatSize(doc.size_bytes)} · {doc.category || "Chưa phân loại"}{doc.related_document ? ` · Sửa đổi của ${doc.related_document}` : ""}</span></div><span className={`document-status ${doc.index_status === "pending" ? "pending" : "active"}`}>{doc.index_status === "pending" ? "Chờ lập chỉ mục" : "Đang dùng"}</span></article>)}
          </div>
          {archive.length > 0 && <details className="admin-archive"><summary>Bản cũ đã lưu trữ ({archive.length})</summary>{archive.map((doc) => <div className="archive-row" key={`${doc.file_name}-${doc.modified_at}`}>{doc.file_name}<span>{new Date(doc.modified_at).toLocaleString("vi-VN")}</span></div>)}</details>}
        </div>
      </div>
    </section>
  );
}

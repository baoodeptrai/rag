import { useEffect, useMemo, useState } from "react";
import { deleteAdminDocument, getAdminDocuments, reindexAdminDocuments, uploadAdminDocument } from "../services/adminService";

const TOKEN_KEY = "uniassist-admin-token";
const formatSize = (size) => size < 1024 * 1024 ? `${(size / 1024).toFixed(0)} KB` : `${(size / (1024 * 1024)).toFixed(1)} MB`;

export default function AdminDocuments() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || "");
  const [tokenInput, setTokenInput] = useState("");
  const [documents, setDocuments] = useState([]);
  const [changeType, setChangeType] = useState("new");
  const [replaceFile, setReplaceFile] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const activeDocs = useMemo(() => documents.filter((doc) => doc.status === "active"), [documents]);
  const pendingCount = activeDocs.filter((doc) => doc.index_status === "pending").length;

  async function refreshDocs(accessToken = token) {
    const result = await getAdminDocuments(accessToken);
    setDocuments(result.documents || []);
  }

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    getAdminDocuments(token).then((result) => {
      if (!cancelled) setDocuments(result.documents || []);
    }).catch((err) => {
      if (cancelled) return;
      setError(err.message);
      if (/401|403/.test(err.message)) {
        sessionStorage.removeItem(TOKEN_KEY);
        setToken("");
      }
    });
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
    setError("");
    setNotice("");
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!file) return setError("Chọn file PDF hoặc DOCX.");
    if (changeType === "replace" && !replaceFile) return setError("Chọn tài liệu cần thay thế.");

    setBusy(true);
    setError("");
    setNotice("");
    const form = new FormData();
    form.append("file", file);
    form.append("change_type", changeType);
    if (changeType === "replace") form.append("related_document", replaceFile);
    try {
      const result = await uploadAdminDocument(token, form);
      setNotice(result.message);
      setFile(null);
      setReplaceFile("");
      event.currentTarget.reset();
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
    setNotice("Đang cập nhật kho tài liệu…");
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

  async function handleDelete(doc) {
    if (!window.confirm(`Xóa “${doc.file_name}” khỏi kho đang dùng? Bản sao sẽ được giữ trong kho lưu trữ.`)) return;
    setBusy(true);
    setError("");
    setNotice(`Đang xóa ${doc.file_name} khỏi kho và cập nhật chỉ mục…`);
    try {
      const result = await deleteAdminDocument(token, doc.file_name);
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
          <p>Thêm PDF/DOCX mới hoặc thay một tài liệu đang có.</p>
          <form onSubmit={unlock} className="admin-login-form">
            <label htmlFor="admin-token">Mã quản trị</label>
            <input id="admin-token" type="password" autoComplete="current-password" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} placeholder="Nhập ADMIN_API_TOKEN" required />
            <button className="primary-button" type="submit">Mở quản trị</button>
          </form>
          <small>Mã được cấu hình trong <code>backend/.env</code>.</small>
          {error && <div className="admin-alert error">{error}</div>}
        </div>
      </section>
    );
  }

  return (
    <section className="admin-page">
      <div className="admin-title-row">
        <div><span className="admin-eyebrow">QUẢN TRỊ</span><h2>Tài liệu</h2><p>Thêm hoặc thay tài liệu PDF/DOCX.</p></div>
        <button className="secondary-button" type="button" onClick={signOut}>Đăng xuất</button>
      </div>
      {error && <div className="admin-alert error">{error}</div>}
      {notice && <div className="admin-alert success">{notice}</div>}

      <div className="admin-grid">
        <form className="admin-card admin-upload-card" onSubmit={handleUpload}>
          <h3>{changeType === "new" ? "Thêm tài liệu" : "Thay tài liệu"}</h3>
          <label htmlFor="change-type">Thao tác</label>
          <select id="change-type" value={changeType} onChange={(e) => { setChangeType(e.target.value); setReplaceFile(""); }}>
            <option value="new">Thêm mới</option>
            <option value="replace">Thay tài liệu đang có</option>
          </select>
          {changeType === "replace" && <>
            <label htmlFor="replace-document">Tài liệu cần thay</label>
            <select id="replace-document" value={replaceFile} onChange={(e) => setReplaceFile(e.target.value)} required>
              <option value="">Chọn tài liệu</option>
              {activeDocs.map((doc) => <option key={doc.file_name} value={doc.file_name}>{doc.file_name}</option>)}
            </select>
          </>}
          <label htmlFor="document-file">File PDF hoặc DOCX</label>
          <input id="document-file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
          <button className="primary-button" type="submit" disabled={busy}>{busy ? "Đang xử lý…" : changeType === "new" ? "Thêm tài liệu" : "Thay tài liệu"}</button>
        </form>

        <div className="admin-card">
          <div className="admin-list-heading"><div><h3>Kho tài liệu</h3><p>{activeDocs.length} tài liệu</p></div><button className="primary-button" type="button" onClick={handleReindex} disabled={busy || activeDocs.length === 0}>{busy ? "Đang cập nhật…" : pendingCount ? `Cập nhật (${pendingCount})` : "Cập nhật kho"}</button></div>
          <div className="admin-document-list">
            {activeDocs.length === 0 && <div className="admin-empty">Chưa có tài liệu.</div>}
            {activeDocs.map((doc) => <article className="admin-document-row" key={doc.file_name}>
              <span className="document-file-icon">▤</span>
              <div className="document-details"><strong>{doc.file_name}</strong><span>{formatSize(doc.size_bytes)}</span></div>
              <span className={`document-status ${doc.index_status === "pending" ? "pending" : "active"}`}>{doc.index_status === "pending" ? "Chờ cập nhật" : "Đang dùng"}</span>
              <button className="secondary-button" type="button" disabled={busy} onClick={() => handleDelete(doc)}>Xóa</button>
            </article>)}
          </div>
        </div>
      </div>
    </section>
  );
}

import { useEffect, useMemo, useState } from "react";
import { analyzeAdminAmendment, approveAdminAmendment, getAdminDocuments, reindexAdminDocuments, updateAdminDocumentMetadata, uploadAdminDocument } from "../services/adminService";

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
  const [documentNumber, setDocumentNumber] = useState("");
  const [supersedesNumber, setSupersedesNumber] = useState("");
  const [publishedAt, setPublishedAt] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveUntil, setEffectiveUntil] = useState("");
  const [metadataFile, setMetadataFile] = useState("");
  const [metadataNumber, setMetadataNumber] = useState("");
  const [metadataPublishedAt, setMetadataPublishedAt] = useState("");
  const [metadataEffectiveFrom, setMetadataEffectiveFrom] = useState("");
  const [metadataEffectiveUntil, setMetadataEffectiveUntil] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [analyzingFile, setAnalyzingFile] = useState("");
  const [approvedByFile, setApprovedByFile] = useState({});

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
    if (changeType === "replace" && !related && !supersedesNumber.trim()) return setError("Chọn tài liệu cũ hoặc nhập số văn bản bị thay thế.");
    setBusy(true);
    setError("");
    setNotice("");
    const form = new FormData();
    form.append("file", file);
    form.append("category", category);
    form.append("change_type", changeType);
    if (related) form.append("related_document", related);
    if (documentNumber.trim()) form.append("document_number", documentNumber.trim());
    if (supersedesNumber.trim()) form.append("supersedes_number", supersedesNumber.trim());
    if (publishedAt) form.append("published_at", publishedAt);
    if (effectiveFrom) form.append("effective_from", effectiveFrom);
    if (effectiveUntil) form.append("effective_until", effectiveUntil);
    try {
      const result = await uploadAdminDocument(token, form);
      setNotice(`${result.file_name}: ${result.message}`);
      setFile(null);
      setDocumentNumber("");
      setSupersedesNumber("");
      setPublishedAt("");
      setEffectiveFrom("");
      setEffectiveUntil("");
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

  function selectMetadataFile(name) {
    setMetadataFile(name);
    const document = activeDocs.find((item) => item.file_name === name);
    setMetadataNumber(document?.document_number || "");
    setMetadataPublishedAt(document?.published_at || "");
    setMetadataEffectiveFrom(document?.effective_from || "");
    setMetadataEffectiveUntil(document?.effective_until || "");
  }

  async function handleMetadataUpdate(event) {
    event.preventDefault();
    if (!metadataFile) return setError("Chọn tài liệu cần cập nhật metadata.");
    setBusy(true);
    setError("");
    setNotice("");
    const form = new FormData();
    form.append("file_name", metadataFile);
    form.append("document_number", metadataNumber.trim());
    form.append("published_at", metadataPublishedAt);
    form.append("effective_from", metadataEffectiveFrom);
    form.append("effective_until", metadataEffectiveUntil);
    try {
      const result = await updateAdminDocumentMetadata(token, form);
      setNotice(result.message);
      await refreshDocs();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAnalyzeAmendment(fileName) {
    setAnalyzingFile(fileName);
    setError("");
    setNotice(`Đang dùng AI local đối chiếu ${fileName} với tài liệu gốc…`);
    try {
      const result = await analyzeAdminAmendment(token, fileName);
      const initial = (result.analysis || []).flatMap((item) => item.classification === "replace" ? item.superseded_chunk_ids : []);
      setApprovedByFile((current) => ({ ...current, [fileName]: [...new Set(initial)] }));
      setNotice(result.message);
      await refreshDocs();
    } catch (err) {
      setError(err.message);
      setNotice("");
    } finally {
      setAnalyzingFile("");
    }
  }

  async function handleApproveAmendment(fileName) {
    const selected = approvedByFile[fileName] || [];
    setBusy(true);
    setError("");
    setNotice("Đang cập nhật chỉ mục theo các đoạn đã duyệt…");
    try {
      const result = await approveAdminAmendment(token, fileName, selected);
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
              <select id="related-document" value={related} onChange={(e) => setRelated(e.target.value)} required={changeType === "replace" && !supersedesNumber.trim() || changeType === "amendment"}>
                <option value="">{changeType === "replace" ? "Chọn tài liệu" : "Không chọn"}</option>
                {activeDocs.map((doc) => <option key={doc.file_name} value={doc.file_name}>{doc.file_name}</option>)}
              </select>
            </>
          )}
          <label htmlFor="doc-category">Nhóm tài liệu</label>
          <select id="doc-category" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="dao_tao">Đào tạo</option><option value="cong_tac_sinh_vien">Công tác sinh viên</option><option value="hoc_phi_hoc_bong">Học phí, học bổng</option><option value="khac">Khác</option>
          </select>
          <label htmlFor="document-number">Số/ký hiệu văn bản</label>
          <input id="document-number" value={documentNumber} onChange={(e) => setDocumentNumber(e.target.value)} placeholder="Ví dụ: 123/TB-HV" />
          <label htmlFor="supersedes-number">Tự lưu trữ văn bản bị thay thế (nếu có)</label>
          <input id="supersedes-number" value={supersedesNumber} onChange={(e) => setSupersedesNumber(e.target.value)} placeholder="Nhập số/ký hiệu đang có trong kho" />
          <div className="admin-help">Khi số này khớp đúng một tài liệu hiện hành, hệ thống lưu trữ bản cũ và tự dựng lại chỉ mục. Cần nhập số văn bản mới ở ô phía trên.</div>
          <label htmlFor="published-at">Ngày ban hành</label>
          <input id="published-at" type="date" value={publishedAt} onChange={(e) => setPublishedAt(e.target.value)} />
          <label htmlFor="effective-from">Hiệu lực từ</label>
          <input id="effective-from" type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
          <label htmlFor="effective-until">Hiệu lực đến (để trống nếu chưa xác định)</label>
          <input id="effective-until" type="date" value={effectiveUntil} onChange={(e) => setEffectiveUntil(e.target.value)} />
          <label htmlFor="document-file">File PDF hoặc Word</label>
          <input id="document-file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(e) => setFile(e.target.files?.[0] || null)} required />
          <div className="admin-help">
            {changeType === "new" && "Tài liệu độc lập sẽ được thêm vào kho hiện hành. Có thể nhập số văn bản bị thay thế ở trường bên trên để hệ thống lưu trữ bản cũ tự động."}
            {changeType === "replace" && "Bản cũ sẽ được lưu trong kho lưu trữ; chỉ bản mới được lập chỉ mục."}
            {changeType === "amendment" && "AI sẽ so sánh từng đoạn với tài liệu gốc đã chọn. Bạn xem và duyệt đề xuất trước khi đoạn cũ bị loại khỏi chỉ mục."}
          </div>
          <button className="primary-button" type="submit" disabled={busy}>{busy ? "Đang xử lý…" : "Tải tài liệu lên"}</button>
        </form>

        <div className="admin-card">
          <div className="admin-list-heading"><div><h3>Tài liệu đang dùng</h3><p>{activeDocs.length} tài liệu</p></div><button className="primary-button" type="button" onClick={handleReindex} disabled={busy || activeDocs.length === 0}>{busy ? "Đang cập nhật…" : pendingCount ? `Cập nhật chỉ mục (${pendingCount})` : "Dựng lại chỉ mục"}</button></div>
          <div className="admin-document-list">
            {activeDocs.length === 0 && <div className="admin-empty">Chưa có tài liệu trong kho.</div>}
            {activeDocs.map((doc) => <article className="admin-document-row" key={doc.file_name}><span className="document-file-icon">▤</span><div className="document-details"><strong>{doc.file_name}</strong><span>{formatSize(doc.size_bytes)} · {doc.category || "Chưa phân loại"}{doc.document_number ? ` · ${doc.document_number}` : ""}{doc.supersedes_number ? ` · Thay thế số ${doc.supersedes_number}` : doc.supersedes_document ? ` · Thay thế ${doc.supersedes_document}` : ""}{doc.related_document ? ` · Sửa đổi của ${doc.related_document}` : ""}{doc.effective_from || doc.effective_until ? ` · Hiệu lực ${doc.effective_from || "không rõ"}–${doc.effective_until || "không thời hạn"}` : ""}</span></div><span className={`document-status ${doc.index_status === "pending" ? "pending" : "active"}`}>{doc.index_status === "pending" ? "Chờ lập chỉ mục" : "Đang dùng"}</span>
              {doc.change_type === "amendment" && <div className="amendment-review">
                <strong>Đối chiếu phiên bản: {doc.revision_status === "approved" ? "Đã duyệt" : doc.revision_status === "review_required" ? "Chờ bạn duyệt" : "Chưa phân tích"}</strong>
                {doc.revision_status !== "approved" && <button type="button" className="secondary-button" disabled={busy || analyzingFile === doc.file_name} onClick={() => handleAnalyzeAmendment(doc.file_name)}>{analyzingFile === doc.file_name ? "AI đang phân tích…" : doc.revision_analysis ? "Phân tích lại bằng AI" : "Phân tích với AI"}</button>}
                {doc.revision_analysis?.map((item) => <div className="revision-proposal" key={item.new_chunk_id}>
                  <div><b>{item.classification.toUpperCase()}</b> · trang mới {item.new_page_number || "?"}{item.new_article ? ` · ${item.new_article}` : ""} · tin cậy {Math.round((item.confidence || 0) * 100)}%</div>
                  <p><b>Đoạn mới:</b> {item.new_text}</p><p>{item.rationale}</p>
                  {item.candidates?.map((old) => { const selected = approvedByFile[doc.file_name] ?? (doc.revision_analysis || []).flatMap((proposal) => proposal.classification === "replace" ? proposal.superseded_chunk_ids : []); return <label className="revision-old-chunk" key={old.chunk_id}><input type="checkbox" disabled={item.classification !== "replace" || doc.revision_status === "approved"} checked={selected.includes(old.chunk_id)} onChange={(event) => setApprovedByFile((current) => ({ ...current, [doc.file_name]: event.target.checked ? [...new Set([...selected, old.chunk_id])] : selected.filter((id) => id !== old.chunk_id) }))} /><span><b>Đoạn cũ · trang {old.page_number || "?"}{old.article ? ` · ${old.article}` : ""}</b><br />{old.text}</span></label>; })}
                </div>)}
                {doc.revision_status === "review_required" && <button type="button" className="primary-button" disabled={busy} onClick={() => handleApproveAmendment(doc.file_name)}>{busy ? "Đang cập nhật…" : `Duyệt lựa chọn & cập nhật chỉ mục (${(approvedByFile[doc.file_name] || doc.revision_analysis.flatMap((item) => item.classification === "replace" ? item.superseded_chunk_ids : [])).length})`}</button>}
              </div>}
            </article>)}
          </div>
          {archive.length > 0 && <details className="admin-archive"><summary>Bản cũ đã lưu trữ ({archive.length})</summary>{archive.map((doc) => <div className="archive-row" key={`${doc.file_name}-${doc.modified_at}`}>{doc.file_name}<span>{new Date(doc.modified_at).toLocaleString("vi-VN")}</span></div>)}</details>}
        </div>
      </div>

      <form className="admin-card admin-upload-card" onSubmit={handleMetadataUpdate}>
        <h3>Hiệu chỉnh metadata tài liệu hiện hành</h3>
        <p>Gán số hiệu/ngày hiệu lực cho tài liệu đã có trong kho. Chỉ mục sẽ được dựng lại để Qdrant nhận metadata mới.</p>
        <label htmlFor="metadata-file">Tài liệu</label>
        <select id="metadata-file" value={metadataFile} onChange={(e) => selectMetadataFile(e.target.value)} required>
          <option value="">Chọn tài liệu</option>
          {activeDocs.map((doc) => <option key={doc.file_name} value={doc.file_name}>{doc.file_name}</option>)}
        </select>
        <label htmlFor="metadata-number">Số/ký hiệu văn bản</label>
        <input id="metadata-number" value={metadataNumber} onChange={(e) => setMetadataNumber(e.target.value)} />
        <label htmlFor="metadata-published">Ngày ban hành</label>
        <input id="metadata-published" type="date" value={metadataPublishedAt} onChange={(e) => setMetadataPublishedAt(e.target.value)} />
        <label htmlFor="metadata-start">Hiệu lực từ</label>
        <input id="metadata-start" type="date" value={metadataEffectiveFrom} onChange={(e) => setMetadataEffectiveFrom(e.target.value)} />
        <label htmlFor="metadata-end">Hiệu lực đến</label>
        <input id="metadata-end" type="date" value={metadataEffectiveUntil} onChange={(e) => setMetadataEffectiveUntil(e.target.value)} />
        <button className="primary-button" type="submit" disabled={busy || activeDocs.length === 0}>{busy ? "Đang cập nhật…" : "Lưu metadata và lập chỉ mục"}</button>
      </form>
    </section>
  );
}

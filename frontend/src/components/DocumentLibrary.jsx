import { useEffect, useState } from "react";
import { getPublicPdfDocuments, getPublicPdfUrl } from "../services/chatService";

const formatSize = (size) => size < 1024 * 1024 ? `${(size / 1024).toFixed(0)} KB` : `${(size / (1024 * 1024)).toFixed(1)} MB`;

export default function DocumentLibrary() {
  const [documents, setDocuments] = useState([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getPublicPdfDocuments().then((items) => {
      if (!cancelled) {
        setDocuments(items);
        setSelected(items[0]?.file_name || "");
      }
    }).catch((err) => {
      if (!cancelled) setError(err.message);
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  const current = documents.find((item) => item.file_name === selected);
  return (
    <section className="reader-page">
      <div className="reader-heading"><div><span className="admin-eyebrow">TÀI LIỆU THAM KHẢO</span><h2>Đọc và tự kiểm tra nguồn</h2><p>Mở tài liệu gốc để đối chiếu nội dung với câu trả lời của trợ lý.</p></div>
        {current && <a className="secondary-button reader-open-link" href={getPublicPdfUrl(current.file_name)} target="_blank" rel="noreferrer">Mở PDF riêng</a>}
      </div>
      {error && <div className="admin-alert error">{error}</div>}
      {loading ? <div className="admin-empty">Đang tải danh sách PDF…</div> : documents.length === 0 ? <div className="admin-empty">Chưa có file PDF trong kho tài liệu.</div> : (
        <div className="reader-layout">
          <aside className="reader-list" aria-label="Danh sách file PDF">
            {documents.map((doc) => <button className={`reader-file ${selected === doc.file_name ? "selected" : ""}`} type="button" key={doc.file_name} onClick={() => setSelected(doc.file_name)}><span>▤</span><span><strong>{doc.file_name}</strong><small>{formatSize(doc.size_bytes)}</small></span></button>)}
          </aside>
          <div className="reader-frame-wrap">{current && <iframe key={current.file_name} className="reader-frame" src={getPublicPdfUrl(current.file_name)} title={`Đọc ${current.file_name}`} />}</div>
        </div>
      )}
    </section>
  );
}

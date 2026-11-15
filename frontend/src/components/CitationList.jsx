import { getPublicPdfUrl } from "../services/chatService";

export default function CitationList({ citations = [] }) {
  if (!citations.length) return null;

  return (
    <section className="citations" aria-label="Nguồn tham khảo">
      <div className="citations-heading"><span>▤</span> Nguồn tham khảo</div>
      <div className="citation-list">
        {citations.map((citation, index) => {
          const metadata = [
            citation.chapter,
            citation.article,
            citation.clause,
            citation.page_number != null ? `Trang ${citation.page_number}` : null,
          ].filter(Boolean);

          const safeUrl = typeof citation.url === "string" &&
            /^https?:\/\//i.test(citation.url);
          const pdfUrl = typeof citation.doc_name === "string" && citation.doc_name.toLowerCase().endsWith(".pdf")
            ? `${getPublicPdfUrl(citation.doc_name)}${citation.page_number ? `#page=${citation.page_number}` : ""}`
            : null;

          return (
            <article className="citation-card" key={citation.id || index}>
              <div className="file-icon">DOC</div>
              <div className="citation-info">
                <strong>{citation.doc_name || "Tài liệu tham khảo"}</strong>
                {metadata.length > 0 && <span>{metadata.join(" · ")}</span>}
                {citation.excerpt && <p className="citation-excerpt">{citation.excerpt}</p>}
                {safeUrl && (
                  <a href={citation.url} target="_blank" rel="noreferrer">
                    Mở tài liệu ↗
                  </a>
                )}
                {pdfUrl && <a href={pdfUrl} target="_blank" rel="noreferrer">Mở PDF tại trang trích dẫn ↗</a>}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

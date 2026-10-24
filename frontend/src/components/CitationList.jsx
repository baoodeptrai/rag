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
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

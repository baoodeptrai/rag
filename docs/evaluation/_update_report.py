from docx import Document
from pathlib import Path
from docx.oxml import OxmlElement
src = Path(r'D:\k\nhóm 2 câu trả lời.docx')
out = Path(r'D:\40 cái\TV4_RAG\docs\evaluation\report_nhom2_cap_nhat_golden_v2.docx')
out.parent.mkdir(parents=True, exist_ok=True)
doc = Document(str(src))

def set_p(i, text):
    p = doc.paragraphs[i]
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]: r.text = ''
    else: p.add_run(text)

def set_cell(cell, text):
    p = cell.paragraphs[0]
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]: r.text = ''
    else: p.add_run(text)

set_p(1, 'Câu hỏi nghiên cứu của nhóm là: trên cùng corpus và 70 câu hỏi có bằng chứng, BM25-only, Dense-only và Hybrid RRF khác nhau thế nào về khả năng đưa bằng chứng chuẩn vào top 5? Với cùng BM25-only, fixed-size chunking có cải thiện so với structure-aware chunking không? BM25-only là baseline từ khóa; Dense-only là baseline vector; Hybrid RRF là phương pháp kết hợp được đánh giá. Lần chạy này chưa đánh giá reranker.')
set_p(5, 'Golden Dataset v2 draft gồm 100 câu hỏi duy nhất dựa trên sổ tay sinh viên: 70 câu có bằng chứng, 15 câu thuộc chủ đề nhưng tài liệu chưa đủ căn cứ và 15 câu ngoài phạm vi. Bộ dữ liệu đánh giá có đáp án chuẩn, trang và đoạn bằng chứng cho nhóm có căn cứ; các nhãn cần được hai người rà soát độc lập trước khi xem là gold. Hiện 100/100 nhãn đang chờ cross-review, nên kết quả dưới đây còn sơ bộ.')
set_p(6, 'Minh chứng: 100 câu (70 có căn cứ, 15 thiếu căn cứ, 15 ngoài phạm vi); trạng thái nhãn: pending independent cross-review.')
set_p(15, 'Nhóm so sánh structure-aware chunking với fixed-size chunking trên cùng một sổ tay sinh viên và cùng BM25-only, top-k=5. Fixed-size dùng 600 token và overlap 80 token. Hai cách được chấm bằng Recall@5, HitRate@5, MRR@5 và latency trung vị.')
set_p(16, 'Minh chứng: cùng 70 câu hỏi answerable, một tài liệu và BM25-only:')
set_p(19, 'Fixed-size nhỉnh hơn nhẹ trong lần chạy này: Recall@5 cao hơn 0,014, HitRate@5 cao hơn 0,014 và MRR@5 cao hơn 0,007. Đây là chênh lệch nhỏ trên một tài liệu, với nhãn chưa được rà soát độc lập; chưa đủ cơ sở để đổi chunking mặc định. Kết quả đo truy xuất, không đo độ chính xác citation hay chất lượng câu trả lời.')
set_p(24, 'Nhóm chạy ba phương pháp trên cùng 70 câu hỏi answerable, lấy top 5 kết quả. Bảng báo cáo Recall@5, HitRate@5, MRR@5 và latency trung vị. Mỗi cấu hình được đo 3 lần sau 1 lượt warm-up; embedding lấy từ cache local.')
set_p(25, 'Minh chứng:')
set_p(31, 'Reranker chưa được đưa vào benchmark. Vì vậy báo cáo không kết luận reranker làm tăng hay giảm chất lượng; đây là phần nằm ngoài phạm vi số liệu hiện có.')
set_p(32, 'Minh chứng: chưa có kết quả Hybrid so với Hybrid + reranker.')
set_p(37, 'Với câu hỏi có căn cứ, cần chấm tính đúng, đủ và groundedness của câu trả lời cùng độ chính xác của citation theo tài liệu/trang/đoạn. Với câu thiếu căn cứ hoặc ngoài phạm vi, cần chấm refusal đúng/sai. Lần chạy hiện tại chỉ là smoke test 3 câu với Qwen3:4b local; chưa đủ mẫu để tính citation accuracy, groundedness, answer accuracy hay refusal accuracy.')
set_p(42, 'Minh chứng: smoke test cục bộ qua backend và Ollama local, 3 câu; không có request error. Median end-to-end latency 3,63 giây trên model đã nạp.')
set_p(43, 'G001 (có căn cứ): trả lời đúng khoảng 10–22 tín chỉ nhưng chưa nêu ngoại lệ học kỳ 3; cần chấm là chưa đầy đủ nếu chuẩn yêu cầu ngoại lệ. Citation có xuất hiện, chưa được chấm độc lập.')
set_p(44, 'G075 (thiếu căn cứ trong chủ đề): hệ thống từ chối và không trả citation. G088 (ngoài phạm vi): hệ thống từ chối câu hỏi tỷ giá và không trả citation. Hai quan sát này chưa tạo thành metric refusal vì smoke test chỉ có một câu mỗi nhóm.')
set_p(48, 'Nhóm dùng paraphrase-multilingual-MiniLM-L12-v2 cho Dense Retrieval trong benchmark hiện tại. Mô hình chạy từ cache local và phù hợp với tài nguyên máy đang dùng. Lựa chọn này không khẳng định MiniLM tốt hơn BGE-M3 hoặc Qwen3-Embedding; chưa có benchmark đối chứng embedding trên cùng dữ liệu.')
set_p(49, 'Trên 70 câu answerable, Dense-only đạt Recall@5 = 0,607, HitRate@5 = 0,614 và MRR@5 = 0,521; latency trung vị 23,6 ms. BM25-only đạt lần lượt 0,936; 0,943; 0,762 và 0,8 ms. Hybrid RRF đạt 0,779; 0,786; 0,643 và 24,4 ms. Trong bộ này, Dense-only thấp hơn BM25; Hybrid cải thiện so với Dense nhưng chưa vượt BM25.')
set_p(50, 'BGE-M3 và Qwen3-Embedding chưa được benchmark trong lần chạy này. Do đó nhóm chưa có số liệu để so sánh chất lượng, latency hay bộ nhớ của các embedding khác.')
set_p(51, 'Phạm vi kết luận: số liệu chỉ phản ánh một sổ tay sinh viên, một phiên bản chunk và bộ nhãn v2 draft đang chờ cross-review. Chưa có kiểm định thống kê, corpus thứ hai hay đánh giá đầy đủ 100 câu bằng Qwen.')
set_p(52, 'Không suy rộng các kết quả hiện tại thành khẳng định chung cho tài liệu khác hoặc embedding khác.')
set_p(55, 'Bảng dưới giữ vai trò và phân công đã ghi trong báo cáo cũ; phần trăm tiến độ chưa được cập nhật bằng dữ liệu của lần chạy benchmark này.')

# Tables: retain the original layout and replace stale evidence values.
# Table 0: research question matrix.
for row, vals in zip(doc.tables[0].rows, [[
    'Câu hỏi nghiên cứu','Baseline','Phương pháp được đánh giá','Chỉ số'],[
    'Trên cùng 70 câu có bằng chứng, phương pháp nào đưa gold evidence vào top 5 tốt nhất?','BM25-only; Dense-only','Hybrid RRF (BM25 + Dense)','Recall@5, HitRate@5, MRR@5, latency trung vị']]):
    for c,v in zip(row.cells, vals): set_cell(c,v)
# Table 1: chunking comparison.
vals = [
 ['Cách chia','Số chunks','Recall@5','HitRate@5','MRR@5','Latency trung vị'],
 ['Structure-aware','87','0,936','0,943','0,762','0,498 ms'],
 ['Fixed-size (600/80)','77','0,950','0,957','0,769','0,478 ms']]
for row, data in zip(doc.tables[1].rows, vals):
    for c,v in zip(row.cells,data): set_cell(c,v)
# Table 2: retrieval benchmark; remove duplicated trailing latency column.
t = doc.tables[2]
for row, data in zip(t.rows, [
 ['Phương pháp','n','k','Recall@5','HitRate@5','MRR@5','Latency trung vị'],
 ['BM25-only','70','5','0,936','0,943','0,762','0,8 ms'],
 ['Dense-only','70','5','0,607','0,614','0,521','23,6 ms'],
 ['Hybrid RRF','70','5','0,779','0,786','0,643','24,4 ms']]):
    for c,v in zip(row.cells,data): set_cell(c,v)
for row in t.rows:
    if len(row.cells) > 7:
        row._tr.remove(row._tr.tc_lst[-1])
# Table 3 was a duplicated research-question table beneath the reranker section; remove the stale duplicate.
parent = doc.tables[3]._element.getparent()
parent.remove(doc.tables[3]._element)
# Table 4 was a malformed stale embedding table; replace with current Dense-only metrics.
t = doc.tables[3]
for row, data in zip(t.rows, [
 ['Embedding','n','k','Recall@5','HitRate@5','MRR@5','Latency trung vị'],
 ['MiniLM Dense-only','70','5','0,607','0,614','0,521','23,6 ms']]):
    for c,v in zip(row.cells,data): set_cell(c,v)
# Historical progress values remain explicitly marked as unrefreshed.
for row in doc.tables[4].rows[1:]:
    set_cell(row.cells[-1], 'Chưa cập nhật trong benchmark v2')

# Correct the original question headings and replace stale evaluation claims.
set_p(17, 'Bảng cho thấy fixed-size nhỉnh hơn nhẹ; không có cơ sở từ lần chạy này để khẳng định cách chia nào tốt hơn nói chung.')
set_p(22, 'Nhóm chạy ba phương pháp trên cùng 70 câu hỏi answerable, lấy top 5 kết quả. Bảng báo cáo Recall@5, HitRate@5, MRR@5 và latency trung vị; mỗi cấu hình được đo 3 lần sau 1 lượt warm-up.')
set_p(24, '')
set_p(28, 'Reranker chưa được đưa vào benchmark. Vì vậy báo cáo không kết luận reranker làm tăng hay giảm chất lượng; đây là phần nằm ngoài phạm vi số liệu hiện có.')
set_p(31, '')
set_p(34, 'Với câu có căn cứ, cần chấm tính đúng, đủ và groundedness của câu trả lời cùng citation theo tài liệu/trang/đoạn. Với câu thiếu căn cứ hoặc ngoài phạm vi, cần chấm refusal đúng/sai. Lần chạy hiện tại mới là smoke test 3 câu với Qwen3:4b local; chưa đủ mẫu để tính các metric này.')
set_p(37, '')
set_p(39, 'G001: trả lời đúng khoảng 10–22 tín chỉ nhưng chưa nêu ngoại lệ học kỳ 3; cần chấm là chưa đầy đủ nếu chuẩn yêu cầu ngoại lệ. Citation có xuất hiện nhưng chưa được chấm độc lập.')
set_p(40, 'G075 (thiếu căn cứ trong chủ đề) và G088 (ngoài phạm vi): hệ thống từ chối và không trả citation. Đây chỉ là quan sát trên một câu mỗi nhóm, chưa tạo thành metric refusal.')
set_p(43, 'Câu 7 — Embedding MiniLM')
set_p(44, 'Nhóm dùng paraphrase-multilingual-MiniLM-L12-v2 cho Dense Retrieval trong benchmark. Embedding chạy từ cache local, phù hợp tài nguyên máy hiện tại. Đây là lựa chọn triển khai, không phải khẳng định MiniLM tốt hơn các embedding khác.')
set_p(45, 'Trên 70 câu answerable, Dense-only đạt Recall@5 = 0,607, HitRate@5 = 0,614 và MRR@5 = 0,521; latency trung vị 23,6 ms. BM25-only đạt lần lượt 0,936; 0,943; 0,762 và 0,8 ms. Hybrid RRF đạt 0,779; 0,786; 0,643 và 24,4 ms. Dense-only thấp hơn BM25; Hybrid cải thiện so với Dense nhưng chưa vượt BM25 trong bộ này.')
set_p(46, 'BGE-M3 và Qwen3-Embedding chưa được benchmark trên cùng dữ liệu. Nhóm chưa có số liệu đối chứng về chất lượng, latency hay bộ nhớ để kết luận mô hình nào phù hợp hơn.')
set_p(47, 'Phạm vi kết luận: một sổ tay sinh viên, một corpus và nhãn Golden Dataset v2 draft đang chờ cross-review. Chưa có kiểm định thống kê, corpus thứ hai, đánh giá Qwen đủ 100 câu hay benchmark reranker.')
for i in [48,49,50,51,52]: set_p(i, '')

# Rebuild ragged legacy tables with consistent columns while retaining their location and style.
def replace_table(old_table, headers, rows):
    old_el = old_table._tbl
    parent = old_el.getparent()
    idx = parent.index(old_el)
    style = old_table.style
    new = doc.add_table(rows=1, cols=len(headers))
    if style is not None: new.style = style
    for c,v in zip(new.rows[0].cells, headers): set_cell(c,v)
    for values in rows:
        cells = new.add_row().cells
        for c,v in zip(cells, values): set_cell(c,v)
    new_el = new._tbl
    parent.remove(new_el)
    parent.remove(old_el)
    parent.insert(idx, new_el)

replace_table(doc.tables[2],
 ['Phương pháp','n','k','Recall@5','HitRate@5','MRR@5','Latency trung vị'],
 [['BM25-only','70','5','0,936','0,943','0,762','0,8 ms'],
  ['Dense-only','70','5','0,607','0,614','0,521','23,6 ms'],
  ['Hybrid RRF','70','5','0,779','0,786','0,643','24,4 ms']])
replace_table(doc.tables[3],
 ['Embedding','n','k','Recall@5','HitRate@5','MRR@5','Latency trung vị'],
 [['MiniLM Dense-only','70','5','0,607','0,614','0,521','23,6 ms']])
doc.core_properties.title = 'Báo cáo đánh giá RAG offline cập nhật Golden Dataset v2'
doc.core_properties.subject = 'Cập nhật kết quả benchmark retrieval, chunking và Qwen local'
doc.save(str(out))
print(out)






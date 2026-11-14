"""Build a 100-question, source-checked draft evaluation set from the v1 CSV.

This only checks answerable evidence strings against the current extracted
chunks. It does not replace independent human review of answers or refusal
labels.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "evaluation" / "golden_dataset_submission.csv"
OUTPUT = ROOT / "docs" / "evaluation" / "golden_dataset_v2_draft.csv"
CHUNKS = ROOT / "backend" / "data" / "processed" / "chunks.jsonl"
SOURCE_DOC = "so-tay-sinh-vien-2026-20260908101355-e.pdf"


def normalized(value: str) -> str:
    return "".join(char.casefold() for char in value if char.isalnum())


# question_id, category, question, expected_answer, page, evidence, chunk IDs
ANSWERABLE = [
    ("G061", "thông tin Học viện", "Học viện Hàng không Việt Nam được thành lập ngày nào và theo quyết định nào?", "Học viện được thành lập ngày 17/07/2006 theo Quyết định số 168/QĐ-TTg của Thủ tướng Chính phủ.", 2,
     ["Học viện Hàng không Việt Nam được thành lập ngày 17 / 07 / 2006 theo Quyết định số 168 / QĐ - TTg của Thủ tướng Chính phủ"], ["0eec50132f2f4139"]),
    ("G062", "đối tượng áp dụng", "Sổ tay sinh viên này dành cho nhóm sinh viên nào?", "Sổ tay dùng cho sinh viên trình độ đại học hệ chính quy của Học viện Hàng không Việt Nam.", 4,
     ["Sổ tay này dùng cho sinh viên trình độ đào tạo đại học hệ chính quy của Học viện Hàng không Việt Nam"], ["889ca640ed177ba3"]),
    ("G063", "cổng sinh viên", "Mật khẩu mặc định ban đầu của tài khoản sinh viên được nêu trong sổ tay là gì?", "Mật khẩu mặc định được nêu là 1111; sinh viên được yêu cầu đổi mật khẩu sau khi đăng nhập.", 6,
     ["mật khẩu được cấp mặc định là 1111"], ["ea7406fd7124a1cf"]),
    ("G064", "VAA Portal", "Địa chỉ Portal sinh viên được ghi trong sổ tay là gì?", "https://portal.vau.edu.vn/ (địa chỉ được chép đúng như sổ tay).", 4,
     ["Portal sinh viên : https : / / portal . vau . edu . vn /"], ["889ca640ed177ba3"]),
    ("G065", "rèn luyện", "Sinh viên đại học cần hoàn thành tối thiểu bao nhiêu ngày rèn luyện Đoàn-Hội trong toàn khóa?", "Tối thiểu 10 ngày rèn luyện trở lên trong toàn khóa.", 7,
     ["hoàn thành đủ từ 10 ngày rèn luyện trở lên trong toàn khóa học đối với sinh viên trình độ đại học"], ["fd8cc4a82d6e366b"]),
    ("G066", "Support VAA", "Trang chủ Support VAA phân loại trạng thái phiếu hỗ trợ thành những trạng thái nào?", "Chờ xử lý, đang xử lý và đã giải quyết.", 67,
     ["Chờ xử lý : phiếu đã gửi và đang chờ bộ phận kỹ thuật tiếp nhận", "Đang xử lý : phiếu đang được chuyên viên xử lý và kiểm tra", "Đã giải quyết : phiếu hỗ trợ đã hoàn thành xử lý"], ["12e3c43ba527b022"] * 3),
    ("G067", "Support VAA", "Ngoài LMS, email và cấp lại mật khẩu, còn những thẻ hỗ trợ nào được liệt kê trên Support VAA?", "Portal Sinh viên, Phần mềm thi trực tuyến và Hỗ trợ khác.", 69,
     ["Portal Sinh viên - Phần mềm thi trực tuyến - Hỗ trợ khác"], ["5b2465740d98d9ed"]),
    ("G068", "Support VAA", "Khi mô tả lỗi trong phiếu hỗ trợ, tài liệu khuyên cung cấp những thông tin nào?", "Mô tả các bước dẫn đến lỗi; nếu có, cung cấp mã môn học, lớp học phần hoặc mã lỗi.", 69,
     ["nêu rõ các bước dẫn đến lỗi , mã môn học , lớp học phần hoặc mã lỗi nếu có"], ["5b2465740d98d9ed"]),
    ("G069", "Support VAA", "Sổ tay khuyên gửi bao nhiêu phiếu cho cùng một sự cố?", "Chỉ gửi một ticket cho mỗi sự cố, không tạo nhiều ticket trùng lặp.", 71,
     ["Chỉ gửi 01 ticket cho sự cố ; không tạo nhiều ticket trùng lặp"], ["873a1f3151f2cb9a"]),
    ("G070", "Support VAA", "Nội dung góp ý trên Support VAA được hỗ trợ tối đa bao nhiêu ký tự?", "Tối đa 5.000 ký tự.", 70,
     ["Nội dung hỗ trợ tối đa 5 . 000 ký tự"], ["2b6d206140e3da44"]),
    ("G071", "Support VAA", "Sổ tay nêu ví dụ những nội dung khảo sát chất lượng nào?", "Ví dụ gồm chất lượng giảng dạy, cơ sở vật chất và sinh viên tốt nghiệp.", 70,
     ["khảo sát chất lượng giảng dạy , cơ sở vật chất hoặc sinh viên tốt nghiệp"], ["2b6d206140e3da44"]),
    ("G072", "LMS", "Trong lớp học phần LMS, tài liệu liệt kê những loại tài nguyên nào?", "File, URL/Link, Video/Media và Forum.", 63,
     ["File ( PDF / DOCX / PPTX ) Bài giảng", "URL / Link Trang web", "Video / Media Bài giảng ghi âm / ghi hình", "Forum Thông báo hoặc thảo luận"], ["207498581ab4ff59"] * 4),
    ("G073", "LMS", "Lịch Calendar trong LMS phân loại sự kiện thành những nhóm nào?", "Global events, Course events, Group events và User events.", 64,
     ["Global events : sự kiện toàn Học viện", "Course events : sự kiện của học phần", "Group events : sự kiện của nhóm", "User events : sự kiện / ghi chú cá nhân"], ["3f24a0ff461d01b5"] * 4),
    ("G074", "thư viện", "Thư viện mở cửa vào thời gian nào trong tuần theo sổ tay?", "Thứ Hai đến thứ Sáu, từ 7:00 đến 19:00; thứ Bảy, Chủ nhật và ngày lễ nghỉ.", 72,
     ["Thứ 2 → Thứ 6 : 7h00 → 19h00", "Thứ 7 , Chủ nhật , ngày lễ : Nghỉ"], ["6e4cc1c88768e851"] * 2),
]

# Questions about student-life services whose requested facts are absent from
# this handbook. Full-PDF term searches were performed; all remain pending
# independent human review because absence labels need careful adjudication.
IN_DOMAIN_UNANSWERABLE = [
    ("G075", "đời sống sinh viên", "Sổ tay cho biết sinh viên đăng ký ở ký túc xá của Học viện bằng cách nào?"),
    ("G076", "đời sống sinh viên", "Tuyến xe buýt nào đón sinh viên đến cơ sở Học viện?"),
    ("G077", "đời sống sinh viên", "Căn tin trong trường mở cửa từ mấy giờ đến mấy giờ?"),
    ("G078", "đời sống sinh viên", "Phí gửi xe máy theo tháng tại Học viện là bao nhiêu?"),
    ("G079", "chuẩn đầu ra", "Sinh viên cần đạt IELTS hoặc TOEIC tối thiểu bao nhiêu điểm để tốt nghiệp?"),
    ("G080", "học phí", "Học phí chính xác mỗi tín chỉ của ngành Kỹ thuật hàng không trong năm học 2026-2027 là bao nhiêu?"),
    ("G081", "học phí", "Sau khi tốt nghiệp, Học viện hoàn tiền học phí trong chính xác bao nhiêu ngày?"),
    ("G082", "học bổng", "Mức tiền cụ thể của học bổng khuyến khích học tập mỗi học kỳ là bao nhiêu?"),
    ("G083", "cơ sở vật chất", "Phòng tập thể thao của Học viện mở cửa đến mấy giờ?"),
    ("G084", "đời sống sinh viên", "Ký túc xá có bao nhiêu chỗ ở dành cho sinh viên năm nhất?"),
    ("G085", "đời sống sinh viên", "Sinh viên có thể nhận suất ăn hỗ trợ miễn phí ở đâu?"),
    ("G086", "cơ sở vật chất", "Sinh viên đặt sân bóng của Học viện qua hệ thống nào?"),
    ("G087", "đời sống sinh viên", "Xe đưa đón sinh viên ra sân bay chạy theo lịch nào?"),
]

OUT_OF_DOMAIN = [
    ("G088", "ngoài phạm vi", "Giá USD/VND hôm nay là bao nhiêu?"),
    ("G089", "ngoài phạm vi", "Giá Bitcoin hiện tại đang tăng hay giảm?"),
    ("G090", "ngoài phạm vi", "Viết giúp tôi một hàm Python để sắp xếp danh sách theo ngày."),
    ("G091", "ngoài phạm vi", "Cho tôi công thức nấu phở bò tại nhà."),
    ("G092", "ngoài phạm vi", "Tỷ số trận bóng đá tối nay sẽ là bao nhiêu?"),
    ("G093", "ngoài phạm vi", "Gợi ý khách sạn nghỉ dưỡng ở Đà Nẵng cuối tuần này."),
    ("G094", "ngoài phạm vi", "Tôi bị đau đầu và sốt, nên uống thuốc gì?"),
    ("G095", "ngoài phạm vi", "Viết một bài thơ chúc mừng sinh nhật cho bạn tôi."),
    ("G096", "ngoài phạm vi", "Ai đang dẫn đầu giải đua Công thức 1 mùa này?"),
    ("G097", "ngoài phạm vi", "Giải thích cách khai thuế thu nhập cá nhân cho người làm tự do."),
    ("G098", "ngoài phạm vi", "Thiết kế lịch tập gym 4 buổi mỗi tuần để tăng cơ."),
    ("G099", "ngoài phạm vi", "Dự báo thời tiết ngày mai ở Hà Nội thế nào?"),
    ("G100", "ngoài phạm vi", "Dân số thế giới hiện tại là bao nhiêu?"),
]

FIELDS = [
    "question_id", "category", "question", "expected_answer", "answerable",
    "expected_refusal_reason", "source_doc", "pipeline_page", "printed_page",
    "article", "gold_evidence", "gold_chunk_ids", "review_status",
    "source_validation", "reviewer_1", "reviewer_2", "adjudication_note",
]


def main() -> None:
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        old_rows = list(csv.DictReader(stream))
    chunks = [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunk_by_id = {row["chunk_id"]: row for row in chunks}

    rows: list[dict[str, str]] = []
    for row in old_rows:
        item = {field: row.get(field, "") for field in FIELDS}
        item["review_status"] = "pending_independent_cross_review"
        item["source_validation"] = "legacy_v1_label_requires_recheck"
        item["adjudication_note"] = ""
        if item["question_id"] == "G059":
            item.update({
                "category": "học bổng",
                "answerable": "true",
                "expected_answer": "Không. Học bổng được xét theo điều kiện và chỉ tiêu đã công bố; Hội đồng xét từ kết quả cao xuống đến hết chỉ tiêu.",
                "expected_refusal_reason": "",
                "source_doc": SOURCE_DOC,
                "pipeline_page": "27",
                "printed_page": "",
                "article": "",
                "gold_evidence": "Căn cứ chỉ tiêu học bổng đã được Giám đốc Học viện quyết định và công bố , Hội đồng xét học bổng của Học viện sẽ xét theo kết quả từ cao xuống thấp đến hết chỉ tiêu",
                "gold_chunk_ids": "7f5e740437b1ea12",
                "source_validation": "matched_current_extracted_chunk; independent_review_pending",
                "adjudication_note": "Reclassified as answerable because the source states scholarship is limited by quota and ranked by results; cross-review pending.",
            })
        if item["question_id"] == "G060":
            item.update({
                "category": "ngoài phạm vi",
                "question": "Tính giúp tôi khoản lãi kép 20 triệu đồng gửi ngân hàng trong 12 tháng.",
                "expected_answer": "Từ chối vì đây là câu hỏi tính toán tài chính ngoài phạm vi sổ tay sinh viên.",
                "expected_refusal_reason": "out_of_scope",
            })
        if item["question_id"] == "G064":
            item["adjudication_note"] = "PDF text shows portal.vau.edu.vn; verify apparent domain typo against the official source before submission."
        if item["answerable"].lower() == "false":
            item["expected_refusal_reason"] = "out_of_scope" if "ngoài phạm vi" in item["category"] or "ngày nghỉ" in item["category"] else "insufficient_evidence"
        rows.append(item)

    for qid, category, question, answer, page, evidence, ids in ANSWERABLE:
        if len(evidence) != len(ids):
            raise ValueError(f"Evidence/chunk mapping length mismatch for {qid}")
        for snippet, chunk_id in zip(evidence, ids):
            chunk = chunk_by_id.get(chunk_id)
            if not chunk or chunk.get("page_number") != page or normalized(snippet) not in normalized(chunk["text"]):
                raise ValueError(f"Evidence does not match source page/chunk for {qid}: {chunk_id}")
        rows.append({
            "question_id": qid, "category": category, "question": question,
            "expected_answer": answer, "answerable": "true", "expected_refusal_reason": "",
            "source_doc": SOURCE_DOC, "pipeline_page": str(page), "printed_page": "",
            "article": "", "gold_evidence": " | ".join(evidence),
            "gold_chunk_ids": ";".join(dict.fromkeys(ids)),
            "review_status": "pending_independent_cross_review",
            "source_validation": "matched_current_extracted_chunk; independent_review_pending",
            "reviewer_1": "", "reviewer_2": "",
            "adjudication_note": "PDF text shows portal.vau.edu.vn; verify apparent domain typo against the official source before submission." if qid == "G064" else "",
        })

    for qid, category, question in IN_DOMAIN_UNANSWERABLE:
        rows.append({
            "question_id": qid, "category": category, "question": question,
            "expected_answer": "Từ chối lịch sự và nêu rằng sổ tay hiện có không cung cấp thông tin này.",
            "answerable": "false", "expected_refusal_reason": "insufficient_evidence",
            "source_doc": "", "pipeline_page": "", "printed_page": "", "article": "",
            "gold_evidence": "", "gold_chunk_ids": "",
            "review_status": "pending_independent_cross_review",
            "source_validation": "candidate_absence_label; full_text_search_performed; human_review_required",
            "reviewer_1": "", "reviewer_2": "", "adjudication_note": "",
        })

    for qid, category, question in OUT_OF_DOMAIN:
        rows.append({
            "question_id": qid, "category": category, "question": question,
            "expected_answer": "Từ chối lịch sự vì câu hỏi nằm ngoài phạm vi sổ tay sinh viên.",
            "answerable": "false", "expected_refusal_reason": "out_of_scope",
            "source_doc": "", "pipeline_page": "", "printed_page": "", "article": "",
            "gold_evidence": "", "gold_chunk_ids": "",
            "review_status": "pending_independent_cross_review",
            "source_validation": "candidate_out_of_scope_label; human_review_required",
            "reviewer_1": "", "reviewer_2": "", "adjudication_note": "",
        })

    if len(rows) != 100 or len({row["question_id"] for row in rows}) != 100:
        raise ValueError(f"Expected 100 unique questions; got {len(rows)}")
    distribution = {
        "answerable": sum(row["answerable"] == "true" for row in rows),
        "insufficient_evidence": sum(row["expected_refusal_reason"] == "insufficient_evidence" for row in rows),
        "out_of_scope": sum(row["expected_refusal_reason"] == "out_of_scope" for row in rows),
    }
    if distribution != {"answerable": 70, "insufficient_evidence": 15, "out_of_scope": 15}:
        raise ValueError(f"Unexpected class distribution: {distribution}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Created {OUTPUT.relative_to(ROOT)}: {distribution}; all new answerable evidence mapped to current chunks.")
    print("All rows remain pending independent cross-review; do not describe this draft as fully human-validated.")


if __name__ == "__main__":
    main()

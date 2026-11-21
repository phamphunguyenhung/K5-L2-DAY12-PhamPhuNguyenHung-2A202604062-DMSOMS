# Rule: CVAT Export Source & Verification

1. Sau khi người dùng đã duyệt / chỉnh sửa thủ công trên CVAT, **bắt buộc** đồng bộ tất cả `tag`, `box`/`shape`, `skeleton` và `points` sang `source="manual"` trên CVAT trước khi export (không để sót `source="file"` hay `source="auto"`).
2. Sau mỗi lần `export_final.zip`, tự động kiểm tra lại `source` của toàn bộ phần tử trong `annotations.xml` và báo rõ kết quả đếm (`manual` vs `file`/`auto`) mà không để người dùng phải hỏi lại.

# Báo cáo Visual Attribute Audit — Lab Day 12 (G12)

- **Repository:** `D:\06-Learning\AIA-VINGROUP\learning\day12\labs\K5-L2-Day12-DMS-OMS-student`
- **CVAT Task / Job:** `http://localhost:8080/tasks/62/jobs/61`
- **Backup trước khi sửa:** `artifacts/g12_audit/cvat_task62_backup_20261121_080256.json` (SHA-256: `3f666bca93d7...`)
- **Export sau khi sửa:** `export_final.zip` (SHA-256: `2b7c30b83bf3d3500b96027ed59ed95db8b969c28e47130382f8a0c5a952d745`)

## 1. Tổng hợp số liệu thực tế
1. **Tổng ảnh đã xem thực tế bằng Vision:** `22` ảnh (`6` DMS `D01..D06` xoay thẳng + crop mặt phóng to; `16` OMS `S01..S08` ghép cặp RGB/IR cạnh nhau).
2. **Tổng số annotation trên CVAT Task 62:** `103` (`22` tags `frame_meta`, `81` shapes: `child_seat=8, face=19, face13=6, hand=11, infant_seat=8, object=7, person=20, phone=2`).
3. **Tổng mục thuộc tính/nhãn đã kiểm tra chi tiết:** `45` mục (trong `attribute_audit.json`).
4. **Giữ nguyên (`KEEP CURRENT`):** `1` mục (`S05_ir.png` `child_seat.occupied=no`), cùng toàn bộ các thuộc tính đã đúng hoặc `unknown` hợp lệ (như `S05_rgb.png` tối mờ, `S07_rgb.png` vùng ngực tối).
5. **AI đề xuất sửa (`AUTO-APPLY CANDIDATE`):** `34` thuộc tính enum có bằng chứng thị giác rõ ràng.
6. **Đã áp dụng lên CVAT Task 62:** `34` thuộc tính (`--apply`, không thay đổi tọa độ/hình học hay số lượng shape).
7. **Còn `unknown` hợp lệ:** `D05.png` `eye_left`/`eye_right` (góc nghiêng/che khuất), `S07_rgb.png` `person.seatbelt` (vùng ngực quá tối).
8. **Trường hợp cần người duyệt (`NEEDS HUMAN REVIEW`):** `10` trường hợp (xem `needs_review.html`):
   - `D02.png` `face.eye_left`: hiện `closed`, đề xuất `open` (cả 2 mắt đều hé nhìn xuống).
   - `D02.png` `object`: box vật thể trên tay (cần duyệt xóa theo `GUIDE.md §4.2`).
   - `D03.png` `face.gaze_zone`: đề xuất `center` (nhìn điện thoại).
   - `D04.png` `face.gaze_zone`: đề xuất `center` (nhìn xuống bảng giữa/đùi).
   - `D05.png` `face.glasses`: thấy gọng kính nghiêng, xác nhận `clear` / `sun` / `unknown`.
   - `D05.png` `phone`: box hiện vẽ nhầm vào logo Audi trên vô lăng (cần duyệt xóa).
   - `D06.png` `face.eye_right`: hiện `open` nhưng `13/13` điểm `face13` đang `occluded` (đề xuất `unknown`).
   - `D06.png` `object`: box chai nước trên tay (cần duyệt xóa theo `GUIDE.md §4.2`).
   - `S04_rgb.png` `rear_left`: đang gán `infant_seat`, trong khi `S04_ir.png` là `child_seat` (cần duyệt đổi lớp).
   - `S06_rgb.png` `rear_right`: đang gán `infant_seat`, trong khi `S06_ir.png` là `child_seat` (cần duyệt đổi lớp).
9. **Mâu thuẫn RGB/IR đã ghi nhận:** `S05_rgb` tối mờ (giữ trống đúng `§4.4-1`) vs `S05_ir` rõ; `S04_rgb` vs `S04_ir` và `S06_rgb` vs `S06_ir` lệch `infant_seat`/`child_seat`; `S01`/`S03`/`S07` có hình nộm trẻ em trong ghế trẻ em.
10. **Kết quả `cabin_check.py`:** `22` ảnh, **`0 lỗi, 2 cảnh báo`** (`D03.png`, `D06.png` `eye_right=open` vs `face13` occluded).
11. **Tình trạng CVAT read-back:** Khớp hoàn toàn (`tags=22, shapes=81`).
12. **Tình trạng `export_final.zip`:** Hợp lệ, đọc lại được bằng `zipfile` và `cabin_check.py`, không chứa ảnh.

## 2. Files xuất ra
- [attribute_audit.json](file:///D:/06-Learning/AIA-VINGROUP/learning/day12/labs/K5-L2-Day12-DMS-OMS-student/attribute_audit.json)
- [attribute_changes.csv](file:///D:/06-Learning/AIA-VINGROUP/learning/day12/labs/K5-L2-Day12-DMS-OMS-student/attribute_changes.csv)
- [needs_review.html](file:///D:/06-Learning/AIA-VINGROUP/learning/day12/labs/K5-L2-Day12-DMS-OMS-student/needs_review.html)
- [export_final.zip](file:///D:/06-Learning/AIA-VINGROUP/learning/day12/labs/K5-L2-Day12-DMS-OMS-student/export_final.zip)
- [check_final.txt](file:///D:/06-Learning/AIA-VINGROUP/learning/day12/labs/K5-L2-Day12-DMS-OMS-student/check_final.txt)

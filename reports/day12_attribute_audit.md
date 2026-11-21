# Báo cáo Visual Attribute Audit (Final) — Lab Day 12 (G12)

- **Repository:** `D:\06-Learning\AIA-VINGROUP\learning\day12\labs\K5-L2-Day12-DMS-OMS-student`
- **CVAT Task / Job:** `http://localhost:8080/tasks/62/jobs/61`
- **Backup trước khi sửa:** `artifacts/g12_audit/cvat_task62_backup_20261121_080256.json` (`sha256=3f666bca93d7...`)
- **Export cuối cùng:** `export_final.zip` (`sha256=6b45633e96e2be25e4268ff062543a0f37aa4b418923ecdc73754badd0d00e09`)

## 1. Số liệu thực tế sau hoàn thiện
1. **Tổng ảnh đã xem thực tế bằng Vision:** `22` ảnh (`6` DMS `D01..D06` xoay thẳng + crop mặt phóng to; `16` OMS `S01..S08` ghép cặp RGB/IR cạnh nhau, lưu tại `qc_evidence/`).
2. **Tổng số annotation trên CVAT Task 62 (Read-back):** `89` (`22` tags `frame_meta`, `67` shapes: `child_seat=10, face=14, face13=6, hand=11, infant_seat=6, object=5, person=14, phone=1`).
3. **Tổng mục thuộc tính/nhãn đã kiểm tra chi tiết:** `45` mục (`attribute_audit.json`, `attribute_changes.csv`).
4. **Giữ nguyên (`KEEP CURRENT`):** `1` mục (`S05_ir` `child_seat.occupied=no`) cùng các giá trị `unknown` hợp lệ (`S05_rgb` tối mờ, `S07_rgb` vùng ngực tối, `D05` góc nghiêng).
5. **AI đề xuất & đã áp dụng (`AUTO-APPLY` + Final Cleanups):**
   - `34` thuộc tính enum có bằng chứng thị giác rõ ràng (`glasses`, `gaze_zone`, `seatbelt`, `hand.on_wheel`, `child_seat.occupied`, `object.type`).
   - Cập nhật schema `child_seat.occupied` thêm `yes` theo `labels_cabin_v1.json` mới và gán `occupied=yes` cho `4` ghế có hình nộm (`S01_rgb`, `S03_rgb`, `S03_ir`, `S07_ir`).
   - Áp dụng `6` chỉnh sửa bổ sung (`D02` `eye_left=open`, `D03`/`D04` `gaze_zone=center`, `D06` `eye_right=unknown`, `S04_rgb`/`S06_rgb` `infant_seat->child_seat`).
   - Xóa `14` box thừa/sai quy ước (`D02`/`D06` `object`, `D05` `phone` logo Audi, và `person`+`face` của hình nộm trẻ em trong ghế trẻ em).
6. **Còn `unknown` hợp lệ:** `D05.png` (`eye_left`/`eye_right`, `glasses` góc nghiêng), `D06.png` (`eye_left`/`eye_right` bị phản xạ LED + che khuất), `S07_rgb.png` (`person.seatbelt` tối).
7. **Mâu thuẫn RGB/IR đã xử lý:** `S04_rgb`/`S06_rgb` đã thống nhất `child_seat` với bản `_ir`; `S05_rgb` giữ trống hợp lệ theo `GUIDE.md §4.4-1`.
8. **Kết quả `cabin_check.py`:** `22` ảnh, **`Kết quả: 0 lỗi, 1 cảnh báo`** (`D03.png` `eye_right=open` khi mắt phải khuất sau sống mũi — đã giải thích trong `check_final.txt`).
9. **Tình trạng CVAT read-back & `export_final.zip`:** Khớp hoàn toàn (`tags=22, shapes=67`), đọc lại hợp lệ, không chứa ảnh.

# Lab Day 12 — Requirements (G12 · DMS & OMS)

- **Repository chính thức:** `https://github.com/VinUni-AI20k/K5-L2-Day12-DMS-OMS-student`
- **Fork cá nhân:** `https://github.com/phamphunguyenhung/K5-L2-Day12-DMS-OMS-student`
- **Branch làm việc:** `feat/day12-g12-dms-oms`
- **Học viên:** Phạm Phú Nguyễn Hùng · MSSV: `2A202604062` · GitHub: `phamphunguyenhung` / `hungpixi`
- **Mã bộ ảnh:** `G12` (gồm `oms/S01..S10` RGB + IR-sim từ SVIRO BMW X5, và `driver/D01..D06` NIR thật từ Drive&Act)
- **Chế độ:** Cá nhân + Review chéo
- **Hạn nộp:** 12:00 trưa ngày hôm sau (GMT+7) trên LMS (`https://aithucchien.vinuni.edu.vn`)

## 1. Phạm vi ảnh
- **22 ảnh cốt lõi (bắt buộc):**
  - OMS (`G12/oms/`): `S01_rgb.png`, `S01_ir.png` … `S08_rgb.png`, `S08_ir.png` (16 ảnh, 960×640).
  - DMS (`G12/driver/`): `D01.png` … `D06.png` (6 ảnh, 1280×1024, xoay 90°: đầu tài xế bên phải ảnh, mặt hướng về x nhỏ, mắt trái có y lớn hơn mắt phải).
- **4 ảnh mở rộng (tùy chọn, task riêng):** `S09_rgb.png`, `S09_ir.png`, `S10_rgb.png`, `S10_ir.png`.

## 2. Schema nhãn (Guideline Cabin v1.0 — `labels_cabin_v1.json`)
1. `frame_meta` (`tag`, đúng 1 tag/ảnh): `modality` (`ir`/`rgb`), `light` (`unknown`/`day`/`night`), `camera_blocked` (`no`/`yes`).
2. `person` (`rectangle`): `seat` (`driver`, `front_passenger`, `rear_left`, `rear_middle`, `rear_right`), `seatbelt` (`unknown`, `worn_correct`, `worn_incorrect`, `not_worn`). Trên SVIRO chỉ dùng `not_worn` hoặc `unknown`.
3. `face` (`rectangle`): `eye_left` (`unknown`/`open`/`closed`), `eye_right` (`unknown`/`open`/`closed`), `glasses` (`unknown`/`none`/`clear`/`sun`), `gaze_zone` (`other`/`road`/`mirror_l`/`mirror_r`/`mirror_c`/`cluster`/`center`/`lap`). OMS chỉ cần box `face` (thuộc tính để `unknown`/`other` hoặc theo quy tắc).
4. `face13` (`skeleton`, 13 điểm): chỉ gán trên DMS (`D01..D06`) khi box `face` rộng ≥ 60 px; mỗi điểm có cờ `occluded` và `outside`.
5. `hand` (`rectangle`): `whose` (`driver`/`passenger`), `side` (`left`/`right` theo người), `on_wheel` (`unknown`/`yes`/`no`).
6. `phone` (`rectangle`): `state` (`held`/`mounted`/`lap`). Chỉ gán khi thấy rõ ít nhất một phần hình dạng điện thoại.
7. `child_seat` (`rectangle`, OMS): `seat`, `occupied` (`unknown`/`no` — không có `yes`).
8. `infant_seat` (`rectangle`, OMS): `seat`, `facing` (`rear`/`front`).
9. `object` (`rectangle`, OMS): `seat`, `type` (`other`/`bag`/`box`/`cup`).

## 3. Quy tắc bắt buộc & Bảo mật dữ liệu
- **Ảnh ở yên trên máy (`RULES.md §2`):** Không commit ảnh (`*.png`, `*.jpg`), không đưa ảnh lên cloud/GitHub/AI chatbot ngoài.
- **Không đoán (`GUIDE.md §4.4`):** Không thấy rõ thì ghi `unknown` (hoặc `occluded`/`outside` cho `face13`).
- **Ghế theo xe:** Camera OMS nhìn từ trước ra sau → bên trái ảnh là `rear_right`, bên phải ảnh là `rear_left`.
- **Trái/phải theo người:** Trên `D01..D06` xoay 90°, mắt trái tài xế có `y` lớn hơn mắt phải.
- **Export:** Định dạng `CVAT for images 1.1`, bỏ chọn `Save images` (chỉ có `annotations.xml` trong `.zip`).
- **Kiểm tra:** `python scripts/cabin_check.py check export_final.zip --expect 22 --manifest G12/oms/manifest.csv --out check_final.txt` phải đạt `Kết quả: 0 lỗi`.

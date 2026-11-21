# Tự đánh giá — Phạm Phú Nguyễn Hùng · G12

## 1. Tự rà soát 4 cảnh

Loại lỗi: `seat_flip`, `wrong_class`, `guess`, `box`, `missing`, `extra`, `lr_flip`, `flag`, `ok`.

| Ảnh | Đối tượng | Loại lỗi | Ghi chú | Đã sửa? |
|---|---|---|---|---|
| `S03_rgb.png` | `infant_seat`, `person` | `extra` | Model GroundingDINO sinh trùng 2 box trên cùng ghế `rear_left` / `rear_right` | Đã sửa bằng bước dedupe theo ghế (`day12_postprocess_qc.py`) |
| `S08_rgb.png` | `infant_seat` | `extra` | Sinh trùng 2 box `infant_seat` ở `rear_left` | Đã sửa bằng bước dedupe theo ghế |
| `D03.png` | `face13` | `ok` (false warn) | `cabin_check` cảnh báo trục x do ảnh xoay 90°; đã kiểm tra trục y (`left_eye_outer.y > right_eye_outer.y`) | Đã xác minh & giải thích trong `check_final.txt` |
| `D01.png` | `person`, `face13` | `ok` | `face13` đủ 13 điểm, trục y đúng quy ước trái/phải theo tài xế | OK |

## 2. Lỗi mình lặp lại nhiều nhất hôm nay

Lỗi: Nhầm/trùng box trên cùng một vị trí ghế OMS (`extra`) khi kết hợp nhiều model detection (`YOLO26l` + `GroundingDINO-tiny`).

Vì sao mình mắc: Chưa áp dụng ràng buộc duy nhất một box chính (`person` / `child_seat` / `infant_seat`) cho mỗi `seat` ngay ở bước hậu xử lý.

Lần sau tránh bằng cách: Luôn chạy Geometry/Seat Deduplication Gate trước khi xuất XML và kiểm tra bằng `cabin_check.py`.

## 3. Ghi chú về disagreement_log

Đã thực hiện `cabin_check diff` với bài của bạn **Trần Nguyễn Phi Long** (`2A202604058`, `CybevisKeishaa`) trên `22` ảnh chung (`62` dòng bất đồng trong `disagreement_log.csv`).
- Điểm bạn của mình đúng và mình đã sửa trong `export_final_v2.zip`:
  - `D02.png` và `D04.png` (`face.glasses`): tài xế đeo kính cận gọng mảnh trong suốt (`clear`), sửa từ `none`/`sun` → `clear`.
  - `S04_ir.png` (`child_seat.occupied`): ghế trống rõ ràng, sửa từ `unknown` → `no`.

## 4. Ghi chú dữ liệu mô phỏng & vật thể dị thường (báo cáo giảng viên / coach)
- Toàn bộ bộ ảnh OMS (`S01..S08`, SVIRO) là ảnh **simulation dùng ma-nơ-canh**, không phải người thật.
- Phát hiện **vật thể dị thường / bất thường** (hình nộm giống trẻ em đặt trong ghế trẻ em mà guideline chưa mô tả chi tiết). Theo hướng dẫn (`GUIDE.md §3`), **chỉ vẽ box ghế (`child_seat` / `infant_seat`), không vẽ box `person` cho trẻ em/ma-nơ-canh**, đồng thời ghi nhận để báo cáo cho các thầy/coach.

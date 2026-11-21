# TEAM — Ngày 12

Mã bộ ảnh: **G12** · Hình thức: cá nhân

| Họ tên | MSSV | Đã gán đủ 22 ảnh? | Review chéo với (peer diff) | Số dòng disagreement đã xử lý |
|---|---|---|---|---|
| Phạm Phú Nguyễn Hùng | 2A202604062 | có | Trần Nguyễn Phi Long (`2A202604058`, GitHub: `CybevisKeishaa`) | 62 |

Ca hai bạn vẫn không thống nhất và đã hỏi coach (ghi tên ảnh + đối tượng):

- `D01..D06` `frame_meta.light`: `unknown` (ảnh NIR không phân biệt ngày/đêm) vs `night`.
- `S01, S03, S07` hình nộm trẻ em trong `child_seat`/`infant_seat` (đã cập nhật theo `labels_cabin_v1.json` mới với `child_seat.occupied=yes`).

## Cá nhân

### PhamPhuNguyenHung-2A202604062
- Phần mình làm: Tự động hóa pipeline DMS/OMS cục bộ, gán & duyệt thủ công 22 ảnh cốt lõi trên CVAT Task 62, review chéo 62 dòng bất đồng với Trần Nguyễn Phi Long (`CybevisKeishaa`), sửa 3 điểm hợp lệ và xuất `export_final_v2.zip` đạt 0 lỗi 0 cảnh báo.
- Điều mình học được hôm nay: Review chéo giúp phát hiện lỗi sót thuộc tính (`D02`/`D04` `glasses=clear`, `S04_ir` `occupied=no`), đồng thời khẳng định tầm quan trọng của `face13`, box `face` trong OMS và không suy đoán trên ảnh RGB quá tối (`S05_rgb`).

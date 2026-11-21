# TEAM — Ngày 12

Mã bộ ảnh: **G12** · Hình thức: cá nhân

| Họ tên | MSSV | Đã gán đủ 22 ảnh? | Review chéo với (peer diff) | Số dòng disagreement đã xử lý |
|---|---|---|---|---|
| Phạm Phú Nguyễn Hùng | 2A202604062 | có (bản nháp AI cục bộ + QC; chờ duyệt tay trên Web Review UI / CVAT) | PEER_NOT_FOUND (chưa tìm thấy học viên khác công khai mã G12 trên GitHub forks; chờ coach ghép cặp) | 0 (chờ ghép cặp) |

Ca hai bạn vẫn không thống nhất và đã hỏi coach (ghi tên ảnh + đối tượng):

- Chưa có (chờ ghép cặp review chéo).

## Cá nhân

### PhamPhuNguyenHung-2A202604062
- Phần mình làm: Tự động hóa pipeline DMS/OMS cục bộ cho 22 ảnh cốt lõi (`S01..S08` RGB+IR, `D01..D06` NIR), kiểm tra schema/geometry bằng `cabin_check.py`, xây dựng Web Review UI cục bộ để rà soát và duyệt nhãn.
- Điều mình học được hôm nay: Phân biệt rõ quy ước ghế theo xe (`rear_right` ở bên trái ảnh OMS nhìn ngược), trái/phải theo người trên ảnh DMS xoay 90° (`left_eye` có `y` lớn hơn), và tách biệt hiện tượng IR-sim (`SVIRO`) với IR thật (`Drive&Act`).

## Ghi chú ca bất thường gửi Coach / Giảng viên
- Bộ ảnh OMS `G12` (`S01..S08`) là ảnh **simulation (ma-nơ-canh)**; có **vật thể dị thường / bất thường** giống trẻ em trên ghế không phải người thật → chỉ gán `child_seat` / `infant_seat`, không gán `person`, và báo cáo để các thầy/coach xem xét bổ sung vào guideline.

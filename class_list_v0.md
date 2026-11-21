# Danh sách lớp v0 — Phạm Phú Nguyễn Hùng · G12

## DMS (ít nhất 6 lớp)

| # | Lớp / thuộc tính | Giá trị | Để làm gì (chức năng DMS) | Nhìn thấy được trên IR? |
|---|---|---|---|---|
| 1 | `person.seatbelt` | worn_correct / worn_incorrect / not_worn / unknown | Cảnh báo tài xế chưa thắt dây hoặc đeo sai cách (dưới nách/sau lưng) | Có, nhưng vùng tối hoặc áo đen có thể che dây thành `unknown` |
| 2 | `face.eye_left` / `eye_right` | open / closed / unknown | Phát hiện nhắm mắt kéo dài (buồn ngủ/ngủ gật) | Có, trừ khi bị đốm phản xạ LED trên kính hoặc kính râm tối |
| 3 | `face.glasses` | none / clear / sun / unknown | Điều chỉnh ngưỡng tin cậy của bộ ước lượng mắt (kính râm làm giảm độ tin cậy nhìn mắt) | Có, nhưng trên NIR một số kính râm trông hơi trong suốt dễ nhầm |
| 4 | `face.gaze_zone` | road / mirror_l / mirror_r / mirror_c / cluster / center / lap / other | Phát hiện tài xế mất tập trung rời mắt khỏi đường quá lâu | Có qua hướng đầu và đồng tử nếu không bị che |
| 5 | `face13` | 13 điểm + cờ occluded/outside | Tính EAR (tỷ lệ mở mắt), tư thế đầu (yaw/pitch/roll) và mức độ ngáp/mở miệng | Có, các điểm bị che đánh cờ `occluded`/`outside` thay vì đoán |
| 6 | `hand` | whose, side, on_wheel (yes/no/unknown) | Phát hiện buông tay khỏi vô lăng hoặc hành vi gây mất tập trung | Có, theo hình dạng bàn tay và vị trí so với vô lăng |
| 7 | `phone` | state (held / mounted / lap) | Cảnh báo sử dụng điện thoại cầm tay khi đang lái xe | Có qua cạnh/màn hình sáng hoặc dáng máy |

## OMS (ít nhất 6 lớp)

| # | Lớp / thuộc tính | Giá trị | Để làm gì (chức năng OMS) | Nhìn thấy được trên IR? |
|---|---|---|---|---|
| 1 | `person` | seat, seatbelt | Đếm số hành khách, nhắc thắt dây an toàn hàng ghế sau | Có (hình dạng cơ thể), nhưng `seatbelt` dễ mất chi tiết trong vùng tối |
| 2 | `face` | box khuôn mặt | Hỗ trợ xác định hướng ngồi, nhận diện có hành khách hay chỉ đồ vật | Có (hình dạng đầu/mặt) |
| 3 | `child_seat` | seat, occupied (no / unknown) | Nhận biết ghế trẻ em đã lắp và trạng thái trống hay có người/vật bên trong | Có (hình dạng khung ghế) |
| 4 | `infant_seat` | seat, facing (rear / front) | Cảnh báo bỏ quên trẻ em và điều khiển túi khí phù hợp hướng lắp nôi | Có (hình dạng nôi và tay xách) |
| 5 | `object` | seat, type (bag / box / cup / other) | Phân biệt đồ vật để trên ghế với người thật (tránh báo giả nhắc dây an toàn) | Có, nhưng vật tối màu hoặc không có họa tiết dễ nhầm loại (`other`) |
| 6 | `frame_meta` | modality, light, camera_blocked | Kiểm soát chất lượng luồng camera (chặn/che ống kính, chuyển chế độ RGB/IR) | Có |

## 2 câu hỏi leo thang

1. Câu hỏi: Trên ảnh NIR (Drive&Act), một số loại kính râm vẫn cho thấy mờ mờ vùng mắt phía sau tròng kính. Khi thấy mờ vùng mắt qua tròng kính tối trên NIR thì `glasses` nên gán `sun` hay `unknown`, và `eye_left`/`eye_right` có được gán `open` nếu chỉ thấy lờ mờ?
   Khung ví dụ: `D03.png`
   Bạn tạm gán thế nào và vì sao: Tạm giữ `glasses = unknown` và `eye_* = unknown` theo quy tắc 4.4-1 ("không thấy rõ thì `unknown`, không đoán").

2. Câu hỏi: Khi một đồ vật (túi xách/cốc) nằm lọt hoàn toàn hoặc một phần trong ghế trẻ em (`child_seat`), `child_seat.occupied` nên đặt là `no` (vì không có trẻ em) hay `unknown`?
   Khung ví dụ: `S02_rgb.png` / `S02_ir.png`
   Bạn tạm gán thế nào và vì sao: Vẽ 2 box riêng (`child_seat` và `object` cùng `seat` theo §4.8), đặt `child_seat.occupied = no` nếu thấy rõ không có trẻ em, hoặc `unknown` nếu đồ vật che khuất lòng ghế.

## 3. Báo cáo điểm bất thường ngoài Guideline (báo giảng viên / coach)
- **Hiện tượng:** Dữ liệu OMS (`S01..S08`) là ảnh simulation dùng ma-nơ-canh; có xuất hiện **vật thể dị thường / bất thường** (hình nộm giống trẻ em/đồ vật lạ trên ghế) chưa được đề cập rõ trong Guideline Cabin v1.0.
- **Cách xử lý tạm thời:** Chỉ vẽ box ghế (`child_seat` / `infant_seat`), **không vẽ `person`** cho hình nộm trẻ em vì không phải người thật, và báo cáo lại cho các thầy/coach.

# Peer Matching — Lab Day 12 (G12)

- **Trạng thái:** `PEER_NOT_FOUND` (tại thời điểm kiểm tra 2026-11-21 14:13 GMT+7 trên 100 fork công khai của `VinUni-AI20k/K5-L2-Day12-DMS-OMS-student`, chưa có fork nào cập nhật `TEAM.md` ghi mã `G12`).
- **Học viên cần ghép:** Phạm Phú Nguyễn Hùng · `2A202604062` · Mã bộ ảnh: `G12`

## Mẫu tin nhắn ghép cặp (gửi trên kênh lớp / hỏi Coach)
> Chào mọi người / Coach, mình là Phạm Phú Nguyễn Hùng (MSSV `2A202604062`), làm cá nhân bộ ảnh **G12** (Lab Day 12 DMS & OMS). Có bạn nào cùng mã **G12** cần ghép cặp review chéo (`cabin_check diff`) không ạ? Mình đã sẵn sàng file `export_final.zip` (không kèm ảnh).

## Quy trình khi có bạn cùng mã G12
1. Lưu file của bạn thành `peer_export_final.zip`.
2. Chạy: `python scripts/cabin_check.py diff export_final.zip peer_export_final.zip --csv disagreement_log.csv`
3. Cùng đối chiếu tối thiểu 5 dòng (hoặc toàn bộ nếu ít hơn 5), điền `verdict`, `guideline_rule`, `action`.
4. Nếu cần sửa, sửa trên CVAT/nhãn của mình, xuất `export_final_v2.zip` và chạy lại `cabin_check.py`.

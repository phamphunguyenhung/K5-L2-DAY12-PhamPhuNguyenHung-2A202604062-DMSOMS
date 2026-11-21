# Khai báo dùng AI — Phạm Phú Nguyễn Hùng

Ghi chú: Không đưa ảnh cabin hay ảnh tài xế (kể cả ảnh chụp màn hình) cho bất kỳ công cụ AI đám mây/chatbot nào. Mọi bước suy luận trên ảnh chỉ chạy bằng model cục bộ trên máy (`YOLO26l`, `GroundingDINO-tiny`, `S3FD+FAN2D`).

| # | Công cụ | Bạn hỏi gì (tóm tắt) | Bạn dùng kết quả thế nào | Bạn có kiểm lại không? Bằng gì? |
|---|---|---|---|---|
| 1 | Antigravity (trợ lý lập trình local) | Hỗ trợ phân tích Guideline Cabin v1.0 (`GUIDE.md`, `SUBMISSION.md`), viết script pipeline chạy model local (`YOLO26l`, `GroundingDINO-tiny`, `FAN2D`), kiểm tra hình học và tạo giao diện Web Review UI | Sinh bản nháp tọa độ + thuộc tính cục bộ, xuất `export_final.zip` chuẩn CVAT 1.1 và giao diện duyệt nhãn | Có, kiểm bằng `scripts/cabin_check.py`, `scripts/cabin_schema.py` và rà soát trực quan qua Web Review UI |

# Mục tiêu ý tưởng vàng theo năm

Mục tiêu được lưu trong `idea_target_groups`; `idea_target_group_members` ánh xạ các đơn vị vào nhóm theo năm. Khóa chính `(year, unit_id)` ngăn một đơn vị được tính vào hai nhóm cùng năm. `idea_target_excluded_units` loại các đơn vị ngừng hoạt động khỏi báo cáo mục tiêu của năm tương ứng.

Startup tạo bảng và chuyển các mục tiêu cũ trong `unit_idea_targets` thành nhóm một đơn vị. Chạy lại không ghi đè các nhóm đã cấu hình. Dữ liệu ý tưởng và đơn vị gốc được giữ nguyên.

Admin và `ie_manager` quản lý tại `/pages/unit-idea-targets`. Khi cần gộp các nhóm đã có, xóa mục tiêu nhóm cũ để giải phóng đơn vị thành viên rồi tạo/cập nhật nhóm chung. Xóa nhóm mục tiêu không xóa ý tưởng.

Dashboard, bảng chi tiết và Excel sử dụng cùng dữ liệu gộp. Lọc tháng chỉ thay đổi số ý tưởng thực tế; mục tiêu luôn là cả năm. Chọn tất cả năm sẽ thống kê đơn vị gốc và không áp dụng nhóm hay loại trừ của riêng năm nào.

## Import bảng 2026

Nguồn đã đối chiếu: `data/idea_targets_2026.json`, gồm 14 nhóm, 15 đơn vị thành viên, LĐTT 2.452, tổng mục tiêu 123. `YTE+Lab` gồm Y tế và Phòng Lab, mục tiêu chung 1. XN4 bị loại khỏi báo cáo mục tiêu năm 2026. Tỷ lệ của PQTĐS để trống theo ảnh; số lượng mục tiêu được nhập nguyên bản, không tính lại từ tỷ lệ.

Từ thư mục backend:

```powershell
python import_idea_targets.py
python import_idea_targets.py --apply
```

Lệnh đầu chỉ đối chiếu tên đơn vị và tổng. `--apply` sao lưu mục tiêu năm 2026 vào `data/target_backups/`, tạo/migrate bảng, sau đó thay thế cấu hình mục tiêu của riêng năm 2026 trong một transaction. Không sửa các năm khác. Không chạy import lại nếu muốn giữ các chỉnh sửa mục tiêu 2026 sau lần nhập đầu.

Script dùng `DATABASE_URL` từ môi trường hoặc `.env` của backend. Không lưu thông tin đăng nhập server trong source code.

Sau khi database đã được migrate/import, máy chạy ứng dụng chỉ cần pull code và restart backend; startup không tự nhập lại bảng 2026.

## View KPI 222

`public.idea_kpi_by_unit_year` thay thế nguồn `xnm222` cũ với các cột `stt`, `nam`, `don_vi`, `muc_tieu_ytv`, `ytv_duyet`. Số `ytv_duyet` năm 2025 là snapshot cố định ghi trong `data/idea_targets_2025.json`; từ năm 2026 trở đi được đếm tự động từ ý tưởng có trạng thái `APPROVED` hoặc `REWARDED` theo năm của `submitted_at`, giống bảng "Ý tưởng theo đơn vị".

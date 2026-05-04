# YÊU CẦU MỞ CỔNG VÀ CHUYỂN HƯỚNG PORT 443
## Gửi: Bộ phận Quản lý An ninh Mạng

**Ngày:** 02/05/2026  
**Người đề xuất:** Nhóm phát triển ứng dụng nội bộ M29  
**Ứng dụng:** Golden Idea Web App (`ytv.hachibavn.com`)

---

## 1. BỐI CẢNH

Công ty đang vận hành hệ thống nội bộ **Golden Idea** — ứng dụng web dùng để tiếp nhận, quản lý và xét duyệt các sáng kiến cải tiến từ nhân viên. Ứng dụng hiện được triển khai tại máy chủ nội bộ IP `172.16.1.144`, phục vụ người dùng qua tên miền `ytv.hachibavn.com` (đi qua Cloudflare proxy).

Một tính năng quan trọng của hệ thống là cho phép nhân viên **đính kèm file minh họa** (hình ảnh, video clip) khi gửi sáng kiến. Các file này có thể lên đến **300MB** (ví dụ: video quay lại quy trình làm việc thực tế).

---

## 2. VẤN ĐỀ HIỆN TẠI

Cloudflare — dịch vụ CDN/proxy đang bảo vệ tên miền chính — có **giới hạn kích thước file upload tối đa là 100MB** ở gói miễn phí/pro. Khi nhân viên cố tải file lớn hơn 100MB, Cloudflare sẽ từ chối request và trả về lỗi `413 Request Entity Too Large` trước khi request kịp đến máy chủ.

**Hệ quả:** Nhân viên không thể đính kèm video dài hoặc file lớn khi gửi sáng kiến, ảnh hưởng trực tiếp đến chất lượng hồ sơ sáng kiến.

---

## 3. GIẢI PHÁP ĐỀ XUẤT

Tạo một **tên miền phụ riêng biệt chỉ cho việc upload file**:

```
upload.hachibavn.com  →  172.16.1.144:443  (KHÔNG qua Cloudflare proxy)
ytv.hachibavn.com     →  Cloudflare proxy  →  172.16.1.144  (giữ nguyên)
```

Khi người dùng upload file, ứng dụng sẽ tự động gửi request đến `upload.hachibavn.com` thay vì qua Cloudflare, giúp bypass giới hạn 100MB. Toàn bộ các thao tác khác (đăng nhập, xem danh sách, phê duyệt...) vẫn đi qua Cloudflare như cũ.

### Yêu cầu kỹ thuật cụ thể:

| Thông số | Giá trị |
|---|---|
| Loại rule | Port Forwarding (NAT) |
| Protocol | TCP |
| WAN Port (cổng ngoài) | 443 |
| Private IP (máy chủ nội bộ) | 172.16.1.144 |
| Private Port (cổng nội bộ) | 443 |

Ngoài ra, yêu cầu **tắt hoặc chuyển cổng Remote Management HTTPS của router** từ cổng 443 sang cổng khác (ví dụ: 8443), để tránh xung đột với rule port forwarding trên.

---

## 4. KIẾN TRÚC BẢO MẬT CỦA GIẢI PHÁP

Mặc dù `upload.hachibavn.com` không đi qua Cloudflare proxy, giải pháp đã được thiết kế với các lớp bảo mật sau:

### 4.1 HTTPS bắt buộc — SSL/TLS đầy đủ
- Máy chủ đang chạy **Caddy** — web server tự động lấy và gia hạn chứng chỉ SSL từ Let's Encrypt qua Cloudflare DNS Challenge.
- Chứng chỉ cho `upload.hachibavn.com` đã được cấp thành công (Let's Encrypt, hợp lệ đến 29/07/2026).
- Toàn bộ traffic đều được mã hóa TLS 1.2/1.3. Không có kết nối HTTP thuần.

### 4.2 Phạm vi endpoint giới hạn tối thiểu
- Caddy chỉ cho phép đúng **1 endpoint duy nhất** qua subdomain upload:
  ```
  POST /api/ideas/{idea_id}/upload
  ```
- Tất cả các URL khác đều bị chặn và trả về **HTTP 404**.
- Giao diện quản trị, trang đăng nhập, dữ liệu người dùng... hoàn toàn không thể truy cập qua `upload.hachibavn.com`.

### 4.3 Giới hạn loại file và kích thước
- Backend chỉ chấp nhận các định dạng được whitelist: `jpg, jpeg, png, gif, mp4, avi, mov`.
- Kích thước tối đa: **300MB/file**.
- File được lưu với tên ngẫu nhiên (UUID), không phản ánh tên gốc trong hệ thống.

### 4.4 Timeout kiểm soát
- Kết nối upload có timeout tối đa **10 phút**. Kết nối treo lâu hơn sẽ bị ngắt tự động, giúp phòng chống một số dạng tấn công giữ kết nối (Slowloris).

### 4.5 CORS kiểm soát nguồn gốc request
- Backend chỉ chấp nhận request upload đến từ `https://ytv.hachibavn.com`.
- Request từ các origin khác sẽ bị từ chối bởi CORS policy.

---

## 5. RỦI RO VÀ BIỆN PHÁP GIẢM THIỂU

| Rủi ro | Mức độ | Biện pháp giảm thiểu |
|---|---|---|
| Tấn công upload file độc hại | Trung bình | Whitelist định dạng file; lưu file với tên UUID; không thực thi file |
| Tấn công DDoS vào endpoint upload | Trung bình | Endpoint chỉ nhận POST; có thể bổ sung rate limiting nếu cần |
| Quét cổng / dò endpoint | Thấp | Tất cả URL ngoài endpoint upload đều trả về 404 |
| Lộ giao diện admin | Không có | Caddy chặn toàn bộ route khác; admin panel không expose qua subdomain này |
| Chứng chỉ SSL hết hạn | Thấp | Caddy tự động gia hạn; cảnh báo nếu gia hạn thất bại |
| Man-in-the-middle | Không có | HTTPS bắt buộc, không có fallback HTTP |

### Rủi ro chấp nhận được:
Endpoint upload không được bảo vệ bởi Cloudflare WAF (do bypass proxy). Đây là đánh đổi có chủ ý: ứng dụng này là **nội bộ**, người dùng là nhân viên công ty, và dữ liệu upload là hình ảnh/video sáng kiến — không phải dữ liệu nhạy cảm.

---

## 6. SO SÁNH VỚI PHƯƠNG ÁN THAY THẾ

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| **Subdomain upload DNS Only** (đề xuất này) | Nhanh, không tốn chi phí, bảo mật đủ cho app nội bộ | Không có Cloudflare WAF cho endpoint upload |
| Nâng cấp Cloudflare Enterprise | Tăng giới hạn upload lên 500MB+ | Chi phí cao (>$200/tháng) |
| Upload thẳng lên S3/R2/MinIO | Bypass hoàn toàn server | Cần refactor backend + frontend, tốn thời gian triển khai |

---

## 7. YÊU CẦU CỤ THỂ

Kính đề nghị bộ phận An ninh Mạng thực hiện các thay đổi sau trên router **DrayTek Vigor2960**:

1. **Tắt hoặc chuyển Remote Management HTTPS** từ cổng 443 sang cổng khác (8443 hoặc tắt hẳn nếu không cần thiết).

2. **Thêm rule Port Forwarding (NAT → Port Redirection)**:
   - Protocol: TCP
   - WAN Port: 443
   - Server IP: `172.16.1.144`
   - Local Port: 443

---

## 8. LIÊN HỆ

Mọi thắc mắc kỹ thuật về cấu hình ứng dụng và bảo mật, vui lòng liên hệ nhóm phát triển qua email: **hachiba@hachibavn.com**

---

*Tài liệu này được chuẩn bị bởi nhóm phát triển ứng dụng Golden Idea — 02/05/2026*

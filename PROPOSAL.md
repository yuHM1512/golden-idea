# Đề xuất Hệ thống Ý tưởng Vàng
### Nền tảng số hóa quản lý – xét duyệt – trao thưởng sáng kiến cải tiến

---

## Mục lục

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Luồng hoạt động (Flow)](#2-luồng-hoạt-động-flow)
3. [Hệ thống chấm điểm](#3-hệ-thống-chấm-điểm-k1--k2--k3)
4. [Chức năng theo từng Role](#4-chức-năng-theo-từng-role)
5. [Thư viện & Quản lý trao thưởng](#5-thư-viện--quản-lý-trao-thưởng)
6. [Thông tin kỹ thuật](#6-thông-tin-kỹ-thuật)

---

## 1. Tổng quan hệ thống

**Ý tưởng Vàng** là hệ thống web nội bộ giúp số hóa toàn bộ quy trình tiếp nhận, xét duyệt và trao thưởng sáng kiến cải tiến từ nhân viên — thay thế hoàn toàn quy trình giấy tờ thủ công hiện tại.

### Mục tiêu

| Mục tiêu | Chi tiết |
|---|---|
| **Số hóa** | Thay phiếu đăng ký giấy bằng form trực tuyến, cho phép upload ảnh/video minh chứng |
| **Minh bạch** | Mọi bước xét duyệt được ghi nhận, có thể tra cứu lịch sử |
| **Tự động hóa** | Tính điểm K1/K2/K3, tạo giấy nhận tiền PDF tự động |
| **Lưu trữ** | Thư viện ý tưởng đã được duyệt, phân loại để tham khảo |
| **Công bằng** | Cơ chế ẩn danh khi gửi ý tưởng, điểm số minh bạch |

### Phân loại ý tưởng

| Mã | Danh mục |
|---|---|
| TOOLS | Công cụ / cữ gá / form / phụ trợ |
| PROCESS | Phương pháp / quy trình |
| DIGITIZATION | Số hóa |
| OTHER | Khác |

---

## 2. Luồng hoạt động (Flow)

### Sơ đồ tổng thể

```
┌─────────────────────────────────────────────────────────────────────┐
│                    QUY TRÌNH ÝT ƯỞNG VÀNG                          │
└─────────────────────────────────────────────────────────────────────┘

  [NHÂN VIÊN]          [KTĐM / PGĐ XN]      [TRƯỞNG BP / GĐ XN]
       │                      │                       │
       ▼                      │                       │
  ┌─────────┐                 │                       │
  │  DRAFT  │ ←── Soạn thảo   │                       │
  └────┬────┘                 │                       │
       │ Gửi ý tưởng          │                       │
       ▼                      │                       │
  ┌───────────┐               │                       │
  │ SUBMITTED │ ──────────────►                       │
  └───────────┘    Nhận xét   │                       │
                   Chấm điểm  │                       │
                  ┌───────────┐                       │
                  │UNDER_REVIEW│──────────────────────►
                  └───────────┘    Phê duyệt cấp BP   │
                                  ┌────────────────┐   │
                                  │ DEPT_APPROVED  │   │
                                  └───────┬────────┘   │
                                          │             │
       [BAN CẢI TIẾN]                    │             │
              │                          │             │
              ◄──────────────────────────┘             │
              │  Chuyển lên Ban cải tiến               │
              ▼                                        │
       ┌───────────────┐                               │
       │ COUNCIL_REVIEW│                               │
       └───────┬───────┘                               │
               │                                       │
       [LÃNH ĐẠO CÔNG TY]                             │
               │                                       │
               ▼                                       │
       ┌─────────────────┐                             │
       │LEADERSHIP_REVIEW│                             │
       └────────┬────────┘                             │
                │ Phê duyệt cuối                       │
                ▼                                      │
         ┌──────────┐                                  │
         │ APPROVED │                                  │
         └────┬─────┘                                  │
              │                                        │
       [THỦ QUỸ / QUẢN LÝ ĐƠN VỊ]                    │
              │                                        │
              ▼                                        │
         ┌─────────┐                                   │
         │ REWARDED│ ←── In giấy nhận tiền (PDF)       │
         └─────────┘     Chi thưởng                    │
                                                       │
                    ┌──────────┐                       │
                    │ REJECTED │ ←── Từ chối ở bất     │
                    └──────────┘     kỳ bước nào       │
```

### Bảng trạng thái chi tiết

| Trạng thái | Ý nghĩa | Người xử lý |
|---|---|---|
| `DRAFT` | Đang soạn thảo, chưa gửi | Nhân viên |
| `SUBMITTED` | Đã gửi, chờ xem xét | Hệ thống |
| `UNDER_REVIEW` | KTĐM/PGĐ XN đang nhận xét & chấm điểm | KTĐM / PGĐ XN |
| `DEPT_APPROVED` | Trưởng BP/GĐ XN đã phê duyệt | Trưởng BP / GĐ XN |
| `COUNCIL_REVIEW` | Ban cải tiến đang xem xét | IE Manager |
| `LEADERSHIP_REVIEW` | Lãnh đạo công ty đang xem xét | BOD Manager |
| `APPROVED` | Đã được duyệt hoàn toàn, chờ chi thưởng | — |
| `REWARDED` | Đã chi thưởng, giấy nhận tiền đã in | Thủ quỹ |
| `REJECTED` | Bị từ chối (có ghi lý do) | Người xét duyệt |
| `CANCELLED` | Người gửi hủy trước khi xét duyệt | Nhân viên |

---

## 3. Hệ thống chấm điểm K1 + K2 + K3

Điểm được chấm bởi **KTĐM / PGĐ XN** tại bước `UNDER_REVIEW`.  
**Tổng điểm = K1 + K2 + K3**

---

### K1 — Tính sáng tạo, tính mới

| Mã | Mô tả | Điểm |
|---|---|---|
| A1 | Hoàn toàn mới — chưa từng có | **10 điểm** |
| A2 | Cải tiến, bổ sung ý tưởng đã có | **5 điểm** |
| A3 | Ý tưởng cũ, đã thực hiện nơi khác | **2 điểm** |

---

### K2 — Khả năng áp dụng

| Mã | Mô tả | Điểm |
|---|---|---|
| EASY | Dễ triển khai | Theo thang |
| NORMAL_EASY | Bình thường – thiên dễ | Theo thang |
| NORMAL_HARD | Bình thường – thiên khó | Theo thang |
| HARD | Khó triển khai | Theo thang |
| DIGITAL_SELF_DEVELOPED | Số hóa – tự phát triển | **3 điểm** |
| DIGITAL_CO_DEVELOPED | Số hóa – đồng phát triển | **3 điểm** |
| DIGITAL_OUTSOURCE | Số hóa – nhờ Ban số hóa | **2 điểm** |

---

### K3 — Hiệu quả, giá trị làm lợi

| Loại | Tiêu chí | Điểm |
|---|---|---|
| **Tiết kiệm thời gian** | Số giờ tiết kiệm/năm | 5 – 100 điểm |
| **Tiết kiệm chi phí** | Số VND tiết kiệm được | 10 – 100 điểm |
| **Không đo lường được** | Giá trị tinh thần / chất lượng | **10 điểm** |

> Lưu ý: Chỉ chọn **một** trong hai loại TIME_SAVED hoặc COST_SAVED, không tính cả hai.

---

### Tính thưởng theo đợt (Reward Batch)

Hệ thống hỗ trợ thiết lập hệ số chi thưởng theo **Quý/Năm**:

```
Tiền thưởng = Tổng điểm × Hệ số (VND/điểm)
```

Admin thiết lập hệ số cho từng quý. Ví dụ: hệ số 5.000 VND/điểm → ý tưởng 20 điểm nhận **100.000 VND**.

---

## 4. Chức năng theo từng Role

### 4.1 Nhân viên (`employee`)

**Mô tả:** Người gửi ý tưởng — bất kỳ nhân viên nào trong công ty.

| Chức năng | Mô tả |
|---|---|
| **Gửi ý tưởng** | Điền phiếu đăng ký: tên, mã NV, đơn vị, danh mục, mô tả chi tiết |
| **Upload minh chứng** | Đính kèm ảnh hoặc video (tối đa 10MB/file) |
| **Chọn ẩn danh** | Tùy chọn ẩn danh khi gửi — tên sẽ không hiển thị trong quá trình xét duyệt |
| **Xem trạng thái** | Theo dõi ý tưởng của mình đang ở bước nào trong quy trình |
| **Hủy ý tưởng** | Hủy ý tưởng ở trạng thái DRAFT hoặc SUBMITTED |
| **Gửi cùng người tham gia** | Điền danh sách người cùng đóng góp (nhóm) |

---

### 4.2 KTĐM / Phó GĐ Xưởng (`sub_dept_manager` / `ie_manager`)

**Mô tả:** Người tiếp nhận đầu tiên, thực hiện nhận xét sơ bộ và **chấm điểm K1/K2/K3**.

| Chức năng | Mô tả |
|---|---|
| **Xem danh sách chờ xét** | Danh sách ý tưởng đang ở trạng thái `SUBMITTED` |
| **Nhận xét & chấm điểm** | Chấm K1, K2, K3 theo tiêu chí; hệ thống tự tính tổng |
| **Ghi chú từng tiêu chí** | Nhập ghi chú giải thích lý do điểm số |
| **Chuyển lên cấp trên** | Chuyển trạng thái sang `UNDER_REVIEW` → `DEPT_APPROVED` |
| **Yêu cầu bổ sung** | Gửi yêu cầu bổ sung thông tin (`REQUEST_INFO`) |
| **Từ chối** | Từ chối với lý do cụ thể |
| **Đề xuất khen thưởng cấp đơn vị** | Đánh dấu `Đề xuất khen cấp đơn vị` khi phù hợp |

---

### 4.3 Trưởng Bộ phận / GĐ Xưởng (`dept_manager`)

**Mô tả:** Phê duyệt cấp bộ phận, quyết định chuyển lên Ban cải tiến hay không.

| Chức năng | Mô tả |
|---|---|
| **Xem danh sách chờ phê duyệt** | Ý tưởng đang ở `UNDER_REVIEW` |
| **Phê duyệt cấp bộ phận** | Chuyển trạng thái sang `DEPT_APPROVED` |
| **Xem điểm số của KTĐM** | Xem kết quả chấm điểm K1/K2/K3 đã có |
| **Yêu cầu bổ sung** | Gửi yêu cầu bổ sung (`REQUEST_INFO`) |
| **Từ chối** | Từ chối với lý do cụ thể |
| **In giấy nhận tiền** | In `PaymentSlip` PDF cho ý tưởng thuộc đơn vị quản lý (sau khi `APPROVED`) |

---

### 4.4 Ban Cải tiến (`ie_manager`)

**Mô tả:** Hội đồng xét duyệt cấp công ty, đánh giá chuyên sâu trước khi trình lãnh đạo.

| Chức năng | Mô tả |
|---|---|
| **Xem danh sách chờ hội đồng** | Ý tưởng ở trạng thái `COUNCIL_REVIEW` |
| **Xem toàn bộ hồ sơ** | Xem mô tả, ảnh/video, điểm số, nhận xét cấp dưới |
| **Phê duyệt & chuyển lên lãnh đạo** | Chuyển sang `LEADERSHIP_REVIEW` |
| **Từ chối** | Từ chối với lý do cụ thể |
| **Xem lịch sử xét duyệt** | Toàn bộ chuỗi action đã thực hiện trên ý tưởng |
| **Quản lý thư viện** | Thêm ý tưởng đã duyệt vào thư viện, gắn tag |

---

### 4.5 Lãnh đạo Công ty (`bod_manager`)

**Mô tả:** Phê duyệt cuối cùng, có quyền cao nhất trong chuỗi xét duyệt.

| Chức năng | Mô tả |
|---|---|
| **Xem danh sách chờ lãnh đạo** | Ý tưởng ở trạng thái `LEADERSHIP_REVIEW` |
| **Phê duyệt cuối** | Chuyển trạng thái sang `APPROVED` |
| **Từ chối** | Từ chối với lý do |
| **Xem báo cáo tổng hợp** | Dashboard tổng số ý tưởng, tỷ lệ phê duyệt, đơn vị dẫn đầu |
| **Xem thư viện** | Truy cập thư viện ý tưởng đã được duyệt |

---

### 4.6 Thủ quỹ (`treasurer`)

**Mô tả:** Quản lý việc chi thưởng, xác nhận đã thanh toán.

| Chức năng | Mô tả |
|---|---|
| **Xem danh sách ý tưởng đã duyệt** | Ý tưởng ở `APPROVED`, chưa chi thưởng |
| **Xác nhận đã chi thưởng** | Đánh dấu `đã thanh toán`, ghi nhận thời điểm |
| **Xem giấy nhận tiền** | Download PDF giấy nhận tiền |
| **Quản lý đợt chi thưởng** | Xem danh sách đợt chi theo quý/năm |
| **Lịch sử thanh toán** | Tra cứu lịch sử chi thưởng đã thực hiện |

---

### 4.7 Đại diện Đơn vị (`unit_represent`)

**Mô tả:** Đầu mối của từng đơn vị/xưởng, hỗ trợ nhân viên và theo dõi tiến độ.

| Chức năng | Mô tả |
|---|---|
| **Xem ý tưởng đơn vị** | Danh sách ý tưởng từ đơn vị mình quản lý |
| **Theo dõi trạng thái** | Xem tiến độ xét duyệt của từng ý tưởng |
| **Hỗ trợ gửi ý tưởng** | Hỗ trợ nhân viên điền phiếu đăng ký nếu cần |
| **Xem thống kê đơn vị** | Tổng số ý tưởng, đã duyệt, chờ xét, từ chối |

---

### 4.8 Quản trị viên (`admin`)

**Mô tả:** Quản lý toàn bộ hệ thống, cấu hình danh mục và người dùng.

| Chức năng | Mô tả |
|---|---|
| **Quản lý người dùng** | Tạo / sửa / vô hiệu hóa tài khoản, phân quyền role |
| **Quản lý đơn vị** | Thêm / sửa đơn vị, bộ phận, gán Quản lý đơn vị |
| **Thiết lập hệ số thưởng** | Cấu hình hệ số VND/điểm theo từng quý/năm |
| **Quản lý bộ tiêu chí chấm điểm** | Tùy chỉnh thang điểm K1/K2/K3 |
| **Xem toàn bộ ý tưởng** | Không giới hạn quyền truy cập |
| **Xem báo cáo & thống kê** | Báo cáo tổng hợp theo đơn vị, thời gian, danh mục |
| **Dashboard hệ thống** | Tổng quan sức khỏe hệ thống |

---

## 5. Thư viện & Quản lý trao thưởng

### Thư viện ý tưởng

Tất cả ý tưởng đạt `APPROVED` trở lên được lưu vào **Thư viện** — kho kiến thức cải tiến nội bộ của công ty.

| Tính năng | Mô tả |
|---|---|
| Tìm kiếm & lọc | Lọc theo danh mục, đơn vị, thời gian, điểm số |
| Xem chi tiết | Xem đầy đủ mô tả, ảnh/video, điểm số, người đề xuất |
| Tag & phân loại | Gắn nhãn để dễ tra cứu sau này |
| Thống kê đóng góp | Bảng xếp hạng cá nhân/đơn vị |

### Quy trình trao thưởng

```
APPROVED
   │
   ▼
[Quản lý đơn vị in Giấy nhận tiền PDF]
   │
   ▼
[Nhân viên ký nhận]
   │
   ▼
[Thủ quỹ xác nhận đã chi]
   │
   ▼
REWARDED ✓
```

**Giấy nhận tiền** được tạo tự động dưới dạng PDF, gồm:
- Tên nhân viên, mã NV, đơn vị
- Tên ý tưởng, điểm số
- Số tiền thưởng (= tổng điểm × hệ số quý)
- Ngày in, chữ ký 4 bên: Lãnh đạo / Trưởng KT-ĐM / Trưởng BP / Nhân viên

---

## 6. Thông tin kỹ thuật

### Tech Stack

| Thành phần | Công nghệ |
|---|---|
| Backend | Python FastAPI |
| Database | PostgreSQL |
| Frontend | HTML / CSS / JavaScript |
| File Storage | Local filesystem (có thể nâng cấp S3) |
| PDF Generation | Tự động từ template |
| Authentication | JWT Token |

### Kiến trúc dữ liệu

```
Users
├── Units (Đơn vị / Xưởng)
│   └── Ideas (Ý tưởng)
│       ├── FileAttachments (Ảnh / Video đính kèm)
│       ├── IdeaScores      (Điểm K1 / K2 / K3)
│       ├── IdeaReviews     (Lịch sử xét duyệt)
│       ├── PaymentSlip     (Giấy nhận tiền)
│       └── ActualBenefit   (Hiệu quả thực tế sau áp dụng)
└── RewardBatch (Đợt chi thưởng theo quý/năm)
```

### API Chính

| Nhóm | Endpoint | Mô tả |
|---|---|---|
| Auth | `POST /api/auth/login` | Đăng nhập |
| Ideas | `POST /api/ideas/` | Gửi ý tưởng mới |
| Ideas | `POST /api/ideas/{id}/upload` | Upload ảnh/video |
| Reviews | `POST /api/reviews/` | Thực hiện xét duyệt |
| Reviews | `GET /api/reviews/pending/` | Danh sách chờ xét của tôi |
| Scores | `POST /api/scores/` | Chấm điểm K1/K2/K3 |
| Payments | `POST /api/payments/slips/{id}/print` | Tạo PDF giấy nhận tiền |
| Library | `GET /api/library/` | Xem thư viện ý tưởng |
| Dashboard | `GET /api/dashboard/` | Thống kê tổng quan |

---

*Tài liệu này mô tả phiên bản hiện tại của hệ thống Ý tưởng Vàng.*  
*Cập nhật lần cuối: 2026-04-29*

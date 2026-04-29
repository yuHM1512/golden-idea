# Golden Idea Web App - API Specification

## Base URL
```
http://localhost:8000/api
```

## Authentication
All endpoints (except `/auth/login`) require JWT token in `Authorization` header:
```
Authorization: Bearer <token>
```

---

## Auth Endpoints

### POST /auth/login
**Login with employee code only (no password required at this phase)**

Request:
```json
{
  "employee_code": "T4880"
}
```

Note: Password-based authentication will be added in Phase 2

Response (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "employee_code": "T4880",
    "full_name": "Nguyễn Khắc Minh Huy",
    "email": "minhhuy@hachibavn.com",
    "phone_number": "0123456789",
    "position": "Kỹ sư",
    "unit_id": 5,
    "role": "EMPLOYEE",
    "is_active": true,
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

---

## Idea Endpoints

### POST /ideas/
**Submit new idea (Phiếu đăng ký ý tưởng)**

Request:
```json
{
  "full_name": "Nguyễn Khắc Minh Huy",
  "employee_code": "T4880",
  "phone_number": "0123456789",
  "position": "Kỹ sư",
  "product_code": "SKU123",
  "category": "DIGITIZATION",
  "description": "Xây dựng công cụ số hoá quản lý thiết bị PCCC...",
  "is_anonymous": true,
  "unit_id": 5
}
```

Response (201):
```json
{
  "id": 42,
  "status": "SUBMITTED",
  "submitted_at": "2024-04-23T10:30:00Z",
  "message": "Ý tưởng của bạn đã được đăng ký thành công"
}
```

### GET /ideas/
**List all ideas (with filters)**

Query Parameters:
- `skip` (int): Pagination offset (default 0)
- `limit` (int): Items per page (default 100)
- `status` (string): Filter by status (SUBMITTED, UNDER_REVIEW, APPROVED, etc)
- `unit_id` (int): Filter by unit
- `category` (string): Filter by category

Response (200):
```json
[
  {
    "id": 42,
    "full_name": "Nguyễn Khắc Minh Huy",
    "category": "DIGITIZATION",
    "status": "SUBMITTED",
    "submitted_at": "2024-04-23T10:30:00Z",
    "description": "Xây dựng công cụ số hoá quản lý thiết bị PCCC..."
  },
  ...
]
```

### GET /ideas/{idea_id}
**Get detailed idea information**

Response (200):
```json
{
  "id": 42,
  "full_name": "Nguyễn Khắc Minh Huy",
  "employee_code": "T4880",
  "phone_number": "0123456789",
  "position": "Kỹ sư",
  "product_code": "SKU123",
  "category": "DIGITIZATION",
  "description": "Xây dựng công cụ số hoá quản lý thiết bị PCCC toàn công ty",
  "is_anonymous": true,
  "status": "UNDER_REVIEW",
  "unit_id": 5,
  "submitter_id": 1,
  "submitted_at": "2024-04-23T10:30:00Z",
  "reviewed_at": "2024-04-24T15:00:00Z",
  "approved_at": null,
  "rejection_reason": null,
  "attachments": [
    {
      "id": 1,
      "original_filename": "diagram.png",
      "file_type": "png",
      "file_size": 2048000,
      "uploaded_at": "2024-04-23T10:35:00Z"
    }
  ]
}
```

### POST /ideas/{idea_id}/upload
**Upload image/video attachment**

Request: Form-data
```
file: <binary file>
```

Constraints:
- Max size: 10 MB
- Allowed types: jpg, jpeg, png, gif, mp4, avi, mov

Response (201):
```json
{
  "id": 1,
  "original_filename": "diagram.png",
  "file_type": "png",
  "file_size": 2048000,
  "uploaded_at": "2024-04-23T10:35:00Z"
}
```

### POST /ideas/{idea_id}/submit
**Finalize submission (move from DRAFT to SUBMITTED)**

Response (200):
```json
{
  "id": 42,
  "status": "SUBMITTED",
  "submitted_at": "2024-04-23T10:30:00Z",
  "message": "Ý tưởng của bạn đã được đăng ký thành công"
}
```

---

## Review Endpoints

### POST /reviews/
**Submit review/approval at current level**

Request:
```json
{
  "idea_id": 42,
  "action": "APPROVE",
  "comment": "Rất hay, nên triển khai sớm"
}
```

Response (201):
```json
{
  "id": 1,
  "idea_id": 42,
  "reviewer_id": 5,
  "level": "TECHNICAL",
  "action": "APPROVE",
  "comment": "Rất hay, nên triển khai sớm",
  "reviewed_at": "2024-04-24T10:00:00Z"
}
```

### GET /reviews/{idea_id}/history
**Get review history for idea**

Response (200):
```json
{
  "technical": {
    "id": 1,
    "idea_id": 42,
    "reviewer_id": 5,
    "level": "TECHNICAL",
    "action": "APPROVE",
    "comment": null,
    "reviewed_at": "2024-04-24T10:00:00Z"
  },
  "dept_head": {
    "id": 2,
    "idea_id": 42,
    "reviewer_id": 10,
    "level": "DEPT_HEAD",
    "action": "APPROVE",
    "comment": "Approve and forward to council",
    "reviewed_at": "2024-04-24T14:00:00Z"
  },
  "council": null,
  "leadership": null
}
```

### GET /reviews/pending/
**Get pending reviews for current user**

Query Parameters:
- `level` (string): Filter by level (TECHNICAL, DEPT_HEAD, COUNCIL, LEADERSHIP)

Response (200):
```json
[
  {
    "idea_id": 42,
    "full_name": "Nguyễn Khắc Minh Huy",
    "category": "DIGITIZATION",
    "description": "Xây dựng công cụ số hoá...",
    "submitted_at": "2024-04-23T10:30:00Z",
    "current_level": "COUNCIL_REVIEW"
  },
  ...
]
```

---

## Score Endpoints

### POST /scores/
**Submit K1/K2/K3 score for idea**

Request:
```json
{
  "idea_id": 42,
  "k1_type": "A1",
  "k1_note": "Hoàn toàn mới, chưa có trong công ty",
  "k2_type": "B1",
  "k2_time_frame": "≤3 ngày",
  "k2_note": "Có thể tự phát triển",
  "k3_measure_type": "COST_SAVED",
  "k3_value": 50000000,
  "k3_note": "Tiết kiệm chi phí thuê ngoài"
}
```

Response (201):
```json
{
  "id": 1,
  "idea_id": 42,
  "scorer_id": 5,
  "k1_type": "A1",
  "k1_score": 10,
  "k1_note": "Hoàn toàn mới, chưa có trong công ty",
  "k2_type": "B1",
  "k2_score": 3,
  "k2_time_frame": "≤3 ngày",
  "k2_note": "Có thể tự phát triển",
  "k3_measure_type": "COST_SAVED",
  "k3_score": 40,
  "k3_value": 50000000,
  "k3_note": "Tiết kiệm chi phí thuê ngoài",
  "total_score": 53,
  "is_final": false,
  "scored_at": "2024-04-24T10:00:00Z"
}
```

### GET /scores/{idea_id}/latest
**Get latest score for idea**

Response (200):
```json
{
  "id": 1,
  "idea_id": 42,
  "scorer_id": 5,
  "k1_type": "A1",
  "k1_score": 10,
  "k2_type": "B1",
  "k2_score": 3,
  "k3_measure_type": "COST_SAVED",
  "k3_score": 40,
  "total_score": 53,
  "is_final": false,
  "scored_at": "2024-04-24T10:00:00Z"
}
```

### GET /scores/guide/k1
**K1 Scoring Reference Guide**

Response (200):
```json
{
  "A1": 10,
  "A2": 5,
  "A3": 2
}
```

### GET /scores/guide/k2
**K2 Scoring Reference Guide**

Response (200):
```json
{
  "B1": 3,
  "B2": 3,
  "B3": 2
}
```

### GET /scores/guide/k3
**K3 Scoring Reference Guide**

Response (200):
```json
{
  "TIME_SAVED_1000_PLUS": 60,
  "TIME_SAVED_500_1000": 40,
  "TIME_SAVED_200_500": 20,
  "TIME_SAVED_50_200": 10,
  "TIME_SAVED_UNDER_50": 5,
  "COST_SAVED_200_MILLION": 100,
  "COST_SAVED_100_200": 60,
  "COST_SAVED_50_100": 40,
  "COST_SAVED_10_50": 20,
  "COST_SAVED_UNDER_10": 10,
  "UNMEASURABLE": 10
}
```

---

## Payment Endpoints

### POST /payments/slips
**Create payment slip (after LEADERSHIP approval)**

Request:
```json
{
  "idea_id": 42
}
```

Response (201):
```json
{
  "id": 1,
  "idea_id": 42,
  "employee_code": "T4880",
  "employee_name": "Nguyễn Khắc Minh Huy",
  "amount": 50000.00,
  "printed_by_manager_id": null,
  "print_date": null,
  "is_printed": false,
  "leadership_signed": false,
  "tech_chief_signed": false,
  "dept_head_signed": false,
  "employee_received": false,
  "created_at": "2024-04-24T16:00:00Z",
  "updated_at": "2024-04-24T16:00:00Z"
}
```

### GET /payments/slips
**List payment slips (for unit managers)**

Query Parameters:
- `skip` (int): Pagination offset
- `limit` (int): Items per page
- `is_printed` (bool): Filter by print status

Response (200):
```json
[
  {
    "id": 1,
    "idea_id": 42,
    "employee_name": "Nguyễn Khắc Minh Huy",
    "amount": 50000.00,
    "is_printed": false,
    "print_date": null,
    "created_at": "2024-04-24T16:00:00Z"
  },
  ...
]
```

### POST /payments/slips/{slip_id}/print
**Print payment slip (generate PDF)**

Response (200):
```json
{
  "message": "Giấy nhận tiền đã được in",
  "pdf_url": "/uploads/slips/slip_001_20240424.pdf"
}
```

### GET /payments/slips/{slip_id}/pdf
**Download payment slip PDF**

Response: PDF file (application/pdf)

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid input data"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Idea not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "description"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Workflow Example

1. **Employee submits idea**
   ```
   POST /ideas/
   → Status: SUBMITTED
   ```

2. **KTĐM/PGĐ XN reviews**
   ```
   POST /reviews/ (action: APPROVE)
   → Status: UNDER_REVIEW → DEPT_APPROVED
   ```

3. **Trưởng bộ phận approves & scores**
   ```
   POST /scores/
   POST /reviews/ (action: FORWARD)
   → Status: COUNCIL_REVIEW
   ```

4. **Ban cải tiến reviews**
   ```
   POST /reviews/ (action: APPROVE)
   → Status: LEADERSHIP_REVIEW
   ```

5. **Lãnh đạo approves**
   ```
   POST /reviews/ (action: APPROVE)
   → Status: APPROVED
   ```

6. **Unit manager prints slip**
   ```
   POST /payments/slips
   POST /payments/slips/{id}/print
   → Status: REWARDED
   ```

---

## Data Enums

### IdeaStatus
- DRAFT
- SUBMITTED
- UNDER_REVIEW
- DEPT_APPROVED
- COUNCIL_REVIEW
- LEADERSHIP_REVIEW
- APPROVED
- REWARDED
- REJECTED
- CANCELLED

### IdeaCategory
- PROCESS (Quy trình)
- EQUIPMENT (Thiết bị)
- QUALITY (Chất lượng)
- SAFETY (An toàn)
- COST (Tiết kiệm chi phí)
- DIGITIZATION (Số hóa)
- HR (Nhân sự)
- ENVIRONMENT (Môi trường)
- OTHER

### UserRole
- EMPLOYEE
- REVIEWER
- DEPT_HEAD
- INNOVATION_COUNCIL
- LEADERSHIP
- UNIT_MANAGER
- ADMIN

### ReviewLevel
- TECHNICAL
- DEPT_HEAD
- COUNCIL
- LEADERSHIP

### ReviewAction
- APPROVE
- REJECT
- REQUEST_INFO
- FORWARD

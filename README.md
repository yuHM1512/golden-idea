# Golden Idea Web App (Hệ thống Ý tưởng Vàng)

**Nền tảng số hóa cho Quá trình đánh giá và xét thưởng Ý tưởng Vàng**

## Stack

- **Backend**: Python FastAPI
- **Database**: PostgreSQL
- **Frontend**: HTML/CSS/JavaScript (to be developed)
- **File Storage**: Local filesystem (can be upgraded to S3/Cloud Storage)

## Architecture Overview

### Database Schema

```
Users (EMPLOYEE, REVIEWER, DEPT_HEAD, INNOVATION_COUNCIL, LEADERSHIP, UNIT_MANAGER, ADMIN)
├── Units (Đơn vị / Bộ phận)
│   ├── Ideas
│   │   ├── FileAttachments (Ảnh / Video)
│   │   ├── IdeaScores (K1/K2/K3)
│   │   ├── IdeaReviews (Multi-level approval)
│   │   └── PaymentSlips (Giấy nhận tiền)
```

### Workflow

```
SUBMITTED (from form)
    ↓
UNDER_REVIEW (KTĐM/PGĐ XN reviews & scores)
    ↓
DEPT_APPROVED (Trưởng BP/GĐ XN approves)
    ↓
COUNCIL_REVIEW (Ban cải tiến reviews)
    ↓
LEADERSHIP_REVIEW (Lãnh đạo công ty reviews)
    ↓
APPROVED (All approvals complete)
    ↓
REWARDED (Payment slip printed)
```

## Setup Instructions

### 1. Create `.env` from template

```bash
cp .env.example .env
# Edit .env with your PostgreSQL connection details
```

Example `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/golden_idea
SECRET_KEY=your-secret-key-here
```

### 2. Create PostgreSQL Database

```bash
createdb golden_idea
# Or via psql:
# psql -U postgres -c "CREATE DATABASE golden_idea;"
```

### 3. Install Dependencies

```bash
cd backend
pip install -r ../requirements.txt
```

### 4. Run Database Migrations (future)

```bash
# Using Alembic
alembic upgrade head
```

### 5. Start Backend Server

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Server runs at: `http://localhost:8000`
API Docs: `http://localhost:8000/docs`

## API Endpoints

### Auth
- `POST /api/auth/login` — Login with employee_code & password
- `POST /api/auth/logout` — Logout
- `GET /api/auth/me` — Get current user

### Ideas
- `POST /api/ideas/` — Submit new idea (Phiếu đăng ký)
- `GET /api/ideas/` — List ideas (with filters)
- `GET /api/ideas/{id}` — Get idea details
- `PUT /api/ideas/{id}` — Update idea (before submission)
- `POST /api/ideas/{id}/upload` — Upload attachment (image/video)
- `DELETE /api/ideas/{id}/attachments/{aid}` — Delete attachment
- `POST /api/ideas/{id}/submit` — Finalize submission
- `POST /api/ideas/{id}/cancel` — Cancel idea

### Reviews
- `POST /api/reviews/` — Submit review/approval
- `GET /api/reviews/{id}/history` — Get review history
- `GET /api/reviews/pending/` — Get pending reviews for current user

### Scores
- `POST /api/scores/` — Submit K1/K2/K3 score
- `GET /api/scores/{idea_id}/latest` — Get latest score
- `GET /api/scores/{idea_id}/history` — Get score history
- `GET /api/scores/guide/k1` — K1 scoring reference
- `GET /api/scores/guide/k2` — K2 scoring reference
- `GET /api/scores/guide/k3` — K3 scoring reference

### Payments
- `POST /api/payments/slips` — Create payment slip (Giấy nhận tiền)
- `GET /api/payments/slips` — List slips for unit manager
- `GET /api/payments/slips/{id}` — Get slip details
- `POST /api/payments/slips/{id}/print` — Print slip (generate PDF)
- `GET /api/payments/slips/{id}/pdf` — Download PDF

## Data Structure

### Form Fields (Phiếu đăng ký ý tưởng)

```
- Họ và tên (full_name) — required
- Mã Nhân Viên (employee_code) — optional
- Đơn vị (unit_id) — required
- Bộ phận (category) — required
- Chức vụ (position) — optional
- Số điện thoại (phone_number) — optional
- Nội dung ý tưởng liên quan (category) — required
- Mã hàng (product_code) — optional
- Mô tả ý tưởng (description) — required
- Upload Ảnh / Video (attachments) — optional
- Ẩn danh (is_anonymous) — default True
```

### Scoring (K1/K2/K3)

**K1 - Tính sáng tạo, tính mới:**
- A1: Hoàn toàn mới = 10 điểm
- A2: Cải tiến bổ sung = 5 điểm
- A3: Ý tưởng cũ = 2 điểm

**K2 - Khả năng áp dụng:**
- B1: Tự phát triển = 3 điểm
- B2: Đồng phát triển = 3 điểm
- B3: Nhờ Ban số hoá = 2 điểm

**K3 - Hiệu quả, giá trị làm lợi:**
- Tiết kiệm thời gian: 5-100 điểm (based on hours/year)
- Tiết kiệm chi phí: 10-100 điểm (based on VND saved)
- Không đo lường được: 10 điểm (intangible value)

**Total Score = K1 + K2 + K3**

## Project Phases

### Phase 1: User Management & Basic Submission
- [ ] User authentication (JWT)
- [ ] User/Unit management (admin)
- [ ] Idea submission form
- [ ] Database schema setup

### Phase 2: Multi-Level Review Workflow
- [ ] TECHNICAL review level
- [ ] DEPT_HEAD approval
- [ ] COUNCIL review
- [ ] LEADERSHIP approval
- [ ] Status transitions

### Phase 3: Scoring System
- [ ] K1/K2/K3 scoring form
- [ ] Auto-calculation of total score
- [ ] Score history tracking

### Phase 4: Payment & Reporting
- [ ] Payment slip generation
- [ ] PDF rendering (Giấy nhận tiền)
- [ ] Print management for unit managers
- [ ] Monthly/annual reports

### Phase 5: Frontend UI
- [ ] Responsive dashboard (by role)
- [ ] Idea submission form
- [ ] Review workflow UI
- [ ] Payment slip printing

## File Structure

```
golden-idea/
├── .env.example
├── .env (create this)
├── requirements.txt
├── README.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── unit.py
│   │   │   ├── idea.py
│   │   │   ├── score.py
│   │   │   ├── review.py
│   │   │   ├── payment.py
│   │   │   └── attachment.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── unit.py
│   │   │   ├── idea.py
│   │   │   ├── score.py
│   │   │   ├── review.py
│   │   │   └── payment.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── ideas.py
│   │   │   ├── reviews.py
│   │   │   ├── scores.py
│   │   │   └── payments.py
│   │   ├── services/ (business logic - to be created)
│   │   ├── dependencies.py (to be created)
│   │   └── utils/ (to be created)
│   └── alembic/ (migrations - to be setup)
├── frontend/
│   ├── index.html
│   ├── pages/
│   ├── css/
│   └── js/
└── uploads/ (created automatically for attachments)
```

## Next Steps

1. **Database**: Create PostgreSQL database with the schema
2. **Implement Phase 1**: User auth & idea submission
3. **Test endpoints**: Use Swagger UI at `/docs`
4. **Frontend**: Build React/vanilla JS dashboard
5. **Deployment**: Docker + nginx

## Notes

- User anonymity: `submitter_id` is stored but not returned in public APIs
- Payment slip printing: 50,000 VND fixed amount per approved idea
- File uploads: Max 10MB, allowed types in config
- Multi-level approval: Automatic state transitions on approval
- K3 scoring: Choose between TIME_SAVED or COST_SAVED (not both)

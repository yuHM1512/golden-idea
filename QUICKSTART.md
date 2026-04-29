# Quick Start - Các Bước Chạy Dự Án

## ✅ Bước 1: Verify Environment

```bash
# Kiểm tra Python version
python --version
# Cần Python 3.8+

# Kiểm tra PostgreSQL chạy chưa
psql -U postgres -c "SELECT version();"
```

---

## ✅ Bước 2: Cài Đặt Dependencies

```bash
# Navigate vào backend folder
cd backend

# Cài đặt từ requirements.txt
pip install -r ../requirements.txt
```

Output mong đợi:
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 sqlalchemy-2.0.23 ...
```

---

## ✅ Bước 3: Kiểm Tra .env

```bash
# Từ folder backend, kiểm tra file .env ở parent directory
cat ../.env

# Verify các giá trị cần thiết:
# DATABASE_URL=postgresql://user:password@localhost:5432/golden_idea
# API_TITLE=Golden Idea Web App
# DEBUG=True
```

Nếu chưa có thì:
```bash
# Copy từ template
cp ../.env.example ../.env

# Edit .env với credentials PostgreSQL của bạn
```

---

## ✅ Bước 4: Kiểm Tra Database Connection

```bash
# Chạy Python console để test kết nối
python -c "
from app.database import engine
from sqlalchemy import text
try:
    with engine.connect() as connection:
        result = connection.execute(text('SELECT 1'))
        print('✓ Database connection successful')
except Exception as e:
    print(f'✗ Error: {e}')
"
```

Expected output:
```
✓ Database connection successful
```

---

## ✅ Bước 5: Tạo Database Tables

```bash
# Chạy server lần đầu để auto-create tables
python -m uvicorn app.main:app --reload

# Hoặc tường minh hơn:
python -c "
from app.database import Base, engine
Base.metadata.create_all(bind=engine)
print('✓ Tables created successfully')
"
```

---

## ✅ Bước 6: Khởi Động Server

```bash
# Từ folder backend
python -m uvicorn app.main:app --reload

# Hoặc chi tiết hơn:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

---

## ✅ Bước 7: Kiểm Tra Server Hoạt Động

### Trong terminal khác, test endpoints:

```bash
# 1. Health check
curl http://localhost:8000/health

# Expected: {"status": "ok", "database": "connected"}

# 2. Root endpoint
curl http://localhost:8000/

# Expected: {"message": "Golden Idea Web App API", "version": "0.1.0", "status": "running"}
```

---

## ✅ Bước 8: Swagger UI

Mở browser và truy cập:
```
http://localhost:8000/docs
```

Bạn sẽ thấy:
- ✓ All endpoints listed
- ✓ Try it out feature
- ✓ Interactive API testing

---

## 🔧 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'sqlalchemy'`
```bash
# Reinstall dependencies
pip install -r ../requirements.txt --force-reinstall
```

### Error: `psycopg2.OperationalError: could not connect to server`
```bash
# Kiểm tra PostgreSQL running
psql -U postgres

# Kiểm tra DATABASE_URL format trong .env
# Should be: postgresql://username:password@localhost:5432/database_name
```

### Error: `FATAL: database "golden_idea" does not exist`
```bash
# Tạo database lại
createdb golden_idea

# Hoặc via psql:
psql -U postgres -c "CREATE DATABASE golden_idea;"
```

### Error: `Permission denied: './uploads'`
```bash
# Create uploads directory
mkdir -p uploads
chmod 755 uploads
```

### Port 8000 đang dùng
```bash
# Dùng port khác
python -m uvicorn app.main:app --port 8001 --reload

# Hoặc kill process
lsof -ti:8000 | xargs kill -9
```

---

## 📊 Full Command Sequence (Tổng Hợp)

```bash
# 1. Navigate to backend
cd backend

# 2. Install dependencies
pip install -r ../requirements.txt

# 3. Verify database connection
python -c "
from app.database import engine
from sqlalchemy import text
with engine.connect() as connection:
    connection.execute(text('SELECT 1'))
print('✓ Database ready')
"

# 4. Create tables
python -c "
from app.database import Base, engine
Base.metadata.create_all(bind=engine)
print('✓ Tables created')
"

# 5. Start server
python -m uvicorn app.main:app --reload

# 6. In another terminal, test
curl http://localhost:8000/health
```

---

## 🎯 Success Indicators

- ✓ Server starts without errors
- ✓ Health check returns `{"status": "ok"}`
- ✓ Swagger UI loads at `/docs`
- ✓ Database tables exist in PostgreSQL
- ✓ `./uploads` directory auto-created

---

## 📝 Log Output Example

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
✓ Database tables initialized

[Server is ready for requests]
```

---

## 🚀 Tiếp Theo

Khi server chạy thành công:

1. **Xem API docs**: http://localhost:8000/docs
2. **Test endpoints**: Try it out trong Swagger
3. **Create seed data**: Thêm users vào database
4. **Implement Phase 1**: Start coding `routers/auth.py`

---

**Bắt đầu bước nào? Cần help với lệnh nào không?**

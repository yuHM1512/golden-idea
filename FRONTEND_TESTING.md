# Frontend Integration Testing Guide

## 🎯 What's Been Created

### Folder Structure
```
frontend/
├── index.html                    # Home page
├── pages/
│   ├── login.html               # Login page
│   └── submit-idea.html         # Idea submission form
├── js/
│   └── api.js                   # API client + helpers
```

### Features
- ✅ Responsive design (Tailwind CSS)
- ✅ Form validation
- ✅ API integration (fetch)
- ✅ File upload support
- ✅ Notification system
- ✅ Loading states
- ✅ LocalStorage for draft saving

---

## 🚀 How to Test

### Step 1: Restart Server with Frontend

```bash
# Terminal, from backend folder
python -m uvicorn app.main:app --port 8015 --reload
```

Output should show:
```
✓ Frontend served from: D:\Data Analyst\Tools\golden-idea\frontend
INFO:     Application startup complete
```

### Step 2: Open Browser

```
http://localhost:8015
```

You should see:
- **Home page** with "Đăng Nhập" button
- **Link to API Swagger UI**

### Step 3: Test Login Page

1. Click **"Đăng Nhập"** button
2. Enter any employee code (e.g., `T4880`, `NV001`)
3. Click **"Đăng Nhập"**
4. Should redirect to **Idea Submission Form**

### Step 4: Fill Idea Form

**Personal Info Section:**
- Họ và tên: `Nguyễn Khắc Minh Huy`
- Mã Nhân Viên: `T4880`
- Số điện thoại: `0123456789`
- Chức vụ: `Kỹ sư`
- Đơn vị: Select any (defaults: Khối Văn phòng, etc.)

**Idea Content Section:**
- Nội dung ý tưởng liên quan: `DIGITIZATION` (Công nghệ & Số hóa)
- Mã hàng: `SKU123` (optional)
- Mô tả ý tưởng:
  ```
  Xây dựng công cụ số hoá quản lý thiết bị PCCC toàn công ty.
  Giúp tiết kiệm thời gian xử lý dữ liệu hàng ngày.
  ```

**Attachments (Optional):**
- Drag & drop image files or click upload area
- Supported: jpg, png, gif, mp4, avi, mov

### Step 5: Submit Form

1. Click **"Gửi ý tưởng"** button
2. Should show **loading spinner**
3. On success:
   - ✅ Green notification: "Ý tưởng đã được gửi thành công!"
   - Form resets
   - Redirects after 2 seconds

### Step 6: Check Database

Verify idea was created:

```bash
# In another terminal
psql -U postgres -d golden_idea -c "SELECT * FROM ideas ORDER BY id DESC LIMIT 1;"
```

You should see your submitted idea with all fields populated.

---

## 🐛 Troubleshooting

### Issue: Frontend not loading (404 on http://localhost:8015)
**Fix:**
```bash
# Check folder exists
ls frontend/
ls frontend/pages/

# Verify frontend path in main.py
# Should be: Path(__file__).parent.parent.parent / "frontend"
# Which resolves to: D:\Data Analyst\Tools\golden-idea\frontend
```

### Issue: Form submission fails with CORS error
**Already Fixed in main.py:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Add `http://localhost:8015` if needed:
```python
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8015"
]
```

### Issue: "POST /api/ideas/ 422 Unprocessable Entity"
**Check:**
- All required fields filled (`*` in form)
- `unit_id` is valid integer
- `category` is one of enum values
- Form data serialization in api.js

Add debug in browser console:
```javascript
console.log(formData);  // Before submitting
```

### Issue: File upload not working
**Check:**
- File size < 10MB
- File type in ALLOWED_EXTENSIONS (jpg, png, gif, mp4, avi, mov)
- Upload folder exists: `backend/uploads/`

---

## 📝 API Endpoints Called from Frontend

| Page | Endpoint | Method | Purpose |
|------|----------|--------|---------|
| submit-idea.html | `/api/ideas/` | POST | Submit new idea |
| submit-idea.html | `/api/ideas/{id}/upload` | POST | Upload attachment |

### Mock Data (No Backend Need Yet)

```javascript
// In api.js
getUnits()        // Returns mock units
getCategories()   // Returns enum values
```

---

## 🎨 Customization

### Change API Base URL

Edit `frontend/js/api.js`:
```javascript
const API_BASE = 'http://localhost:8015/api';  // Change port here
```

### Add More Pages

1. Create `frontend/pages/new-page.html`
2. Copy structure from `submit-idea.html`
3. Add API calls in `<script>` section
4. Link in navigation

Example:
```html
<a href="/pages/new-page.html">New Page</a>
```

### Styling

All styling uses Tailwind CSS via CDN. To customize:

1. Edit color classes (already in HTML)
2. Modify Tailwind config in `<script id="tailwind-config">` section
3. Or add to `<style>` section for custom CSS

---

## ✅ Success Checklist

- [ ] Server running at port 8015
- [ ] Frontend loads at http://localhost:8015
- [ ] Login page loads
- [ ] Can enter employee code
- [ ] Redirects to form page
- [ ] Form shows all fields
- [ ] Units dropdown populated
- [ ] Category dropdown populated
- [ ] Can fill form
- [ ] File upload area works
- [ ] Submit button triggers API call
- [ ] API returns 200 success
- [ ] Notification shows
- [ ] Database has new idea record
- [ ] Can logout and login again

---

## 🚢 Next Steps

- [ ] Implement remaining API endpoints (GET /units, etc)
- [ ] Create dashboard page (list ideas)
- [ ] Create review workflow pages
- [ ] Create payment slip page
- [ ] Add authentication (JWT)
- [ ] Build frontend bundle (React/Vue)

---

## 📞 Debug Commands

```bash
# Watch server logs
tail -f app.log

# Check API
curl http://localhost:8015/health

# Check database
psql -U postgres -d golden_idea -c "\dt"

# Clear localStorage (browser console)
localStorage.clear()
```

---

**You're ready to test!** 🎉

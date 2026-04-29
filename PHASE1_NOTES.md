# Phase 1 Implementation Notes

## Simplified for Initial Development

To speed up Phase 1 development, password-based authentication has been **commented out** and will be added in Phase 2.

### What Changed

#### 1. **User Model** (`models/user.py`)
```python
# COMMENTED OUT - will uncomment in Phase 2
# hashed_password = Column(String(255), nullable=False)
```

#### 2. **UserCreate Schema** (`schemas/user.py`)
```python
class UserCreate(BaseModel):
    employee_code: str
    full_name: str
    email: EmailStr
    # ...
    # COMMENTED OUT - will uncomment in Phase 2
    # password: str
```

#### 3. **UserLogin Schema** (`schemas/user.py`)
```python
class UserLogin(BaseModel):
    """Simple login: only need employee_code (no password for now)"""
    employee_code: str
    # COMMENTED OUT - will uncomment in Phase 2
    # password: str
```

#### 4. **Auth Router** (`routers/auth.py`)
```python
@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login endpoint - authenticate user by employee_code only
    TODO: Add password verification in Phase 2
    """
```

#### 5. **Config** (`config.py` & `.env.example`)
```python
# JWT settings commented out - will use when implementing password auth
# JWT_ALGORITHM: str = "HS256"
# JWT_EXPIRATION_HOURS: int = 24
```

#### 6. **Requirements** (`requirements.txt`)
```
# Password-related dependencies commented out
# python-jose[cryptography]==3.3.0
# passlib[bcrypt]==1.7.4
```

---

## Phase 1 Login Flow (Simplified)

```
User enters: employee_code (e.g., "T4880")
    ↓
Query database: SELECT * FROM users WHERE employee_code = 'T4880'
    ↓
Check if user exists and is_active = True
    ↓
Generate JWT token with user_id as subject
    ↓
Return token + user info
```

### Simple Implementation Example

```python
@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    # 1. Find user by employee_code
    user = db.query(User).filter(
        User.employee_code == credentials.employee_code,
        User.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Employee not found")
    
    # 2. Generate JWT token (simple payload)
    token_data = {
        "sub": str(user.id),
        "employee_code": user.employee_code,
        "role": user.role
    }
    access_token = create_access_token(token_data)
    
    # 3. Return response
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user  # Pydantic will serialize
    }
```

---

## Database Setup (No Password Needed)

When creating users in Phase 1, simply provide:
```sql
INSERT INTO users (
    employee_code, full_name, email, unit_id, role, is_active
) VALUES (
    'T4880', 'Nguyễn Khắc Minh Huy', 'minhhuy@hachibavn.com', 5, 'EMPLOYEE', true
);
```

Or via Pydantic (without password field):
```python
user_data = {
    "employee_code": "T4880",
    "full_name": "Nguyễn Khắc Minh Huy",
    "email": "minhhuy@hachibavn.com",
    "unit_id": 5,
    "role": "EMPLOYEE"
}
```

---

## Seed Data Script Needed

Create `backend/app/scripts/seed_db.py` to populate initial users:

```python
from app.database import SessionLocal
from app.models import User, Unit

# Example users
users_data = [
    {
        "employee_code": "T4880",
        "full_name": "Nguyễn Khắc Minh Huy",
        "email": "minhhuy@hachibavn.com",
        "unit_id": 1,
        "role": "EMPLOYEE"
    },
    {
        "employee_code": "REVIEWER001",
        "full_name": "Reviewer User",
        "email": "reviewer@hachibavn.com",
        "unit_id": 1,
        "role": "REVIEWER"
    },
    # ... more users
]
```

---

## Phase 2 TODO (Add Password)

When ready to add password-based authentication:

1. **Un-comment in User Model**
   ```python
   hashed_password = Column(String(255), nullable=False)
   ```

2. **Un-comment in Schemas**
   ```python
   # UserCreate.password: str
   # UserLogin.password: str
   ```

3. **Install Dependencies**
   ```bash
   pip install python-jose[cryptography] passlib[bcrypt]
   ```

4. **Implement Password Hashing**
   ```python
   from passlib.context import CryptContext
   
   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
   
   def hash_password(password: str) -> str:
       return pwd_context.hash(password)
   
   def verify_password(plain: str, hashed: str) -> bool:
       return pwd_context.verify(plain, hashed)
   ```

5. **Update Login Logic**
   ```python
   # Verify password
   if not verify_password(credentials.password, user.hashed_password):
       raise HTTPException(status_code=401, detail="Invalid credentials")
   ```

6. **Enable JWT Settings**
   ```python
   # Uncomment in config.py
   JWT_ALGORITHM: str = "HS256"
   JWT_EXPIRATION_HOURS: int = 24
   ```

7. **Implement Token Expiration**
   ```python
   from datetime import datetime, timedelta
   from jose import jwt
   
   def create_access_token(data: dict, expires_delta: timedelta = None):
       to_encode = data.copy()
       if expires_delta:
           expire = datetime.utcnow() + expires_delta
       else:
           expire = datetime.utcnow() + timedelta(hours=24)
       to_encode.update({"exp": expire})
       encoded_jwt = jwt.encode(
           to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
       )
       return encoded_jwt
   ```

---

## Current Status

✓ Database schema is password-proof (column commented, not deleted)
✓ Pydantic schemas simplified (password field commented)
✓ Auth router ready for simple employee_code lookup
✓ All dependencies can be installed without password packages
✓ JWT infrastructure ready to enable in Phase 2

**Start Phase 1 with just employee_code authentication!** 🚀

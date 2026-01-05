import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, RegisterResponse
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import hash_password, verify_password

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.security import create_access_token, SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


router = APIRouter(tags=["Auth"])

# -------------------------
# REGISTER
# -------------------------
@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()

    # ✅ DOMAIN RESTRICTION
    if not email.endswith("@avocarbon.com"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only @avocarbon.com email addresses are allowed to register",
        )

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="EMPLOYEE",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
    )



# -------------------------
# LOGIN (NO JWT YET)
# -------------------------
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role
    })

    return TokenResponse(access_token=token)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role
    }


from app.core.permissions import require_roles
from app.core.roles import ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN


@router.get("/employee-area")
def employee_area(
    user=Depends(require_roles([ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN]))
):
    return {
        "message": "Employee area",
        "user": user.email,
        "role": user.role
    }


@router.get("/manager-area")
def manager_area(
    user=Depends(require_roles([ROLE_MANAGER, ROLE_ADMIN]))
):
    return {
        "message": "Manager area",
        "user": user.email,
        "role": user.role
    }


@router.get("/admin-area")
def admin_area(
    user=Depends(require_roles([ROLE_ADMIN]))
):
    return {
        "message": "Admin area",
        "user": user.email,
        "role": user.role
    }

"""
Authentication Router for FinanceApp

Endpoints:
- POST /register - Create new user account
- POST /login - Authenticate and get JWT token
- GET /me - Get current user profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from ..database import get_db
from ..models import User
from ..schemas import (
    UserCreate, UserRead, UserLogin, Token, TokenData, UserUpdate
)
from ..utils import (
    hash_password, verify_password, create_access_token, 
    decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============================================
# DEPENDENCIES
# ============================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    print(f"[DEBUG] Token received: {token[:50]}..." if token else "[DEBUG] No token")
    
    try:
        payload = decode_access_token(token)
        print(f"[DEBUG] Payload decoded: {payload}")
        user_id_str = payload.get("sub")
        if user_id_str is None:
            print("[DEBUG] No 'sub' in payload")
            raise credentials_exception
        user_id = int(user_id_str)  # Convert string back to int
    except Exception as e:
        print(f"[DEBUG] Token decode error: {e}")
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        print(f"[DEBUG] User not found with id: {user_id}")
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )
    
    print(f"[DEBUG] User authenticated: {user.email}")
    return user


# ============================================
# ENDPOINTS
# ============================================

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    - **nome**: Full name
    - **email**: Unique email address
    - **celular**: Mobile phone (optional)
    - **senha**: Password (min 6 characters)
    - **confirmar_senha**: Password confirmation
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )
    
    # Create new user
    new_user = User(
        nome=user_data.nome,
        email=user_data.email,
        celular=user_data.celular,
        senha_hash=hash_password(user_data.senha)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    
    Uses OAuth2 password flow:
    - **username**: Email address
    - **password**: User password
    """
    # Find user by email
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )
    
    # Create access token - sub must be string per JWT spec
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile.
    """
    return current_user


@router.put("/me", response_model=UserRead)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.
    
    - **nome**: Update name (optional)
    - **celular**: Update phone (optional)
    """
    if user_data.nome is not None:
        current_user.nome = user_data.nome
    if user_data.celular is not None:
        current_user.celular = user_data.celular
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

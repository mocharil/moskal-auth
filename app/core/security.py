from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
import secrets

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_token(subject: Union[str, int], expires_delta: Optional[timedelta] = None, token_type: str = "access") -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    if token_type == "refresh":
        to_encode["type"] = "refresh"
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_access_token(subject: Union[str, int], expires_delta: Optional[timedelta] = None) -> str:
    return create_token(subject, expires_delta, "access")

def create_refresh_token(subject: Union[str, int], expires_delta: Optional[timedelta] = None) -> str:
    if not expires_delta:
        expires_delta = timedelta(days=7)  # Default 7 days for refresh token
    return create_token(subject, expires_delta, "refresh")

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)

def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)

def is_token_expired(expiration_time: datetime) -> bool:
    return datetime.utcnow() > expiration_time

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        user_id = verify_token(token)
        if user_id is None:
            raise credentials_exception
        # Convert user_id to integer since it's stored as string in the token
        user_id = int(user_id)
    except (JWTError, ValueError):
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

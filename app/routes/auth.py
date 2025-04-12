from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token,
    verify_token, generate_verification_token, generate_password_reset_token,
    is_token_expired, get_current_user
)
from utils.send_email import send_verification_email, send_reset_password_email
from app.schemas.user import (
    UserCreate, UserLogin, UserChangePassword, UserForgotPassword,
    UserResetPassword, UserVerifyEmail, Token, User, UserResponse,
    LoginResponse, UserChangeEmail
)
from app.models.user import User as UserModel
from typing import Optional

router = APIRouter(

    tags=["authentication"]
)

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    if db.query(UserModel).filter(UserModel.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    db_user = UserModel(
        name=user.name,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        verification_token=generate_verification_token()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Send verification email with direct API endpoint
    verification_url = f"{settings.BASE_URL}/api/v1/auth/verify-email?token={db_user.verification_token}"
    try:
        send_verification_email(user.email, verification_url)
    except Exception as e:
        # If email sending fails, still create the user but log the error
        print(f"Failed to send verification email: {str(e)}")
    
    return UserResponse(
        status="success",
        message="User registered successfully. Please check your email for verification.",
        data=db_user
    )

@router.post("/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Authenticate user
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is verified (if verification is required)
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your email first"
        )
    
    return LoginResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
        user=user
    )

@router.post("/refresh-token", response_model=Token)
async def refresh_token(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Verify user still exists
    user = db.query(UserModel).filter(UserModel.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return Token(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
        token_type="bearer"
    )

from fastapi.security import HTTPBearer

security = HTTPBearer()

@router.get("/me", response_model=UserResponse, dependencies=[Depends(security)])
async def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    return UserResponse(
        status="success",
        message="User information retrieved successfully",
        data=current_user
    )

@router.post("/forgot-password", response_model=UserResponse)
async def forgot_password(user_data: UserForgotPassword, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == user_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate and save reset token
    reset_token = generate_password_reset_token()
    user.reset_password_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
    db.commit()
    
    # Send reset password email
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    try:
        send_reset_password_email(user_data.email, reset_url)
    except Exception as e:
        print(f"Failed to send password reset email: {str(e)}")
    
    return UserResponse(
        status="success",
        message="Password reset instructions sent to your email"
    )

@router.post("/reset-password", response_model=UserResponse)
async def reset_password(reset_data: UserResetPassword, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(
        UserModel.reset_password_token == reset_data.token
    ).first()
    
    if not user or is_token_expired(user.reset_token_expires):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.reset_password_token = None
    user.reset_token_expires = None
    db.commit()
    
    return UserResponse(
        status="success",
        message="Password reset successfully"
    )

@router.post("/change-password", response_model=UserResponse)
async def change_password(
    password_data: UserChangePassword,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return UserResponse(
        status="success",
        message="Password changed successfully"
    )

from fastapi.responses import HTMLResponse

@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(
        UserModel.verification_token == token
    ).first()
    
    if not user:
        error_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Verification Failed</title>
            <style>
                body {{
                    font-family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                .container {{
                    background-color: white;
                    padding: 2rem;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    text-align: center;
                    max-width: 400px;
                    width: 90%;
                }}
                .icon {{
                    color: #dc3545;
                    font-size: 4rem;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    color: #dc3545;
                    margin-bottom: 1rem;
                }}
                p {{
                    color: #666;
                    line-height: 1.6;
                }}
                .button {{
                    display: inline-block;
                    padding: 0.8rem 1.5rem;
                    background-color: #dc3545;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 1rem;
                    transition: background-color 0.3s;
                }}
                .button:hover {{
                    background-color: #c82333;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">❌</div>
                <h1>Verification Failed</h1>
                <p>Sorry, the verification link is invalid or has expired. Please request a new verification link.</p>
                <a href="{settings.FRONTEND_URL}/login" class="button">Go to Login</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)
    
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    success_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email Verification Success</title>
        <style>
            body {{
                    font-family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
                background-color: #f5f5f5;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .container {{
                background-color: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 400px;
                width: 90%;
            }}
            .icon {{
                color: #28a745;
                font-size: 4rem;
                margin-bottom: 1rem;
            }}
            h1 {{
                color: #28a745;
                margin-bottom: 1rem;
            }}
            p {{
                color: #666;
                line-height: 1.6;
            }}
            .button {{
                display: inline-block;
                padding: 0.8rem 1.5rem;
                background-color: #28a745;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 1rem;
                transition: background-color 0.3s;
            }}
            .button:hover {{
                background-color: #218838;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">✅</div>
            <h1>Email Verified!</h1>
            <p>Your email has been successfully verified. You can now log in to your account.</p>
                <a href="{settings.FRONTEND_URL}/login" class="button">Go to Login</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=success_html)

@router.post("/change-email", response_model=UserResponse)
async def change_email(
    email_data: UserChangeEmail,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify current email matches
    if email_data.current_email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current email is incorrect"
        )

    # Verify current password
    if not verify_password(email_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Check if new email is already taken
    if db.query(UserModel).filter(
        UserModel.email == email_data.new_email,
        UserModel.id != current_user.id
    ).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Update email and reset verification status
    current_user.email = email_data.new_email
    current_user.is_verified = False
    current_user.verification_token = generate_verification_token()
    db.commit()
    
    # Send verification email
    verification_url = f"{settings.BASE_URL}/api/v1/auth/verify-email?token={current_user.verification_token}"
    try:
        send_verification_email(email_data.new_email, verification_url)
    except Exception as e:
        print(f"Failed to send verification email: {str(e)}")
    
    return UserResponse(
        status="success",
        message="Email updated successfully. Please check your new email for verification.",
        data=current_user
    )

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from app.models.database import get_db, User
from app.models.schemas import Token, UserResponse

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint for user authentication"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate SECRET_KEY is configured
        if not settings.secret_key or settings.secret_key.strip() == "":
            logger.error("SECRET_KEY is not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error: SECRET_KEY is not set. Please configure SECRET_KEY in your .env file."
            )
        
        # Query user from database
        try:
            user = db.query(User).filter(User.username == form_data.username).first()
        except Exception as db_error:
            logger.error(f"Database error during login: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection error. Please try again later."
            )
        
        # Verify user exists and password is correct
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Create access token
        try:
            access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
            access_token = create_access_token(
                data={"sub": user.username, "role": user.role.value},
                expires_delta=access_token_expires
            )
        except Exception as token_error:
            logger.error(f"Error creating access token: {token_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error generating authentication token. Please check server configuration."
            )
        
        return {"access_token": access_token, "token_type": "bearer"}
    
    except HTTPException:
        # Re-raise HTTP exceptions (like 401, 403) as-is
        raise
    except Exception as e:
        # Catch any other unexpected errors
        logger.exception(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during login: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


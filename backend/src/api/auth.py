from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from src.services.auth_service import auth_service, get_current_user, security
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class SignUpRequest(BaseModel):
    """Sign up request model"""

    email: EmailStr
    password: str


class SignInRequest(BaseModel):
    """Sign in request model"""

    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    """Password reset request model"""

    email: EmailStr


class AuthResponse(BaseModel):
    """Authentication response model"""

    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    expires_at: Optional[str] = None


@router.post("/signup", response_model=AuthResponse, tags=["Authentication"])
async def sign_up(request: SignUpRequest):
    """Sign up a new user"""
    try:
        result = await auth_service.sign_up(request.email, request.password)
        return AuthResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sign up error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sign up failed: {str(e)}",
        )


@router.post("/signin", response_model=AuthResponse, tags=["Authentication"])
async def sign_in(request: SignInRequest):
    """Sign in an existing user"""
    try:
        result = await auth_service.sign_in(request.email, request.password)
        return AuthResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sign in error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/signout", response_model=AuthResponse, tags=["Authentication"])
async def sign_out(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Sign out the current user"""
    try:
        result = await auth_service.sign_out(credentials.credentials)
        return AuthResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sign out error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/reset-password", response_model=AuthResponse, tags=["Authentication"])
async def reset_password(request: PasswordResetRequest):
    """Send password reset email"""
    try:
        result = await auth_service.reset_password(request.email)
        return AuthResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/me", tags=["Authentication"])
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get current user information"""
    return current_user


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""

    refresh_token: str


@router.post("/refresh", response_model=AuthResponse, tags=["Authentication"])
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token"""
    try:
        result = await auth_service.refresh_token(request.refresh_token)
        return AuthResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# Debug endpoints (disabled in production)
# @router.get("/debug/users/{email}", tags=["Debug"])
# async def debug_user_by_email(email: str):
#     """Debug endpoint to check user status by email"""
#     try:
#         result = await auth_service.debug_user_by_email(email)
#         return result
#     except Exception as e:
#         logger.error(f"Debug user error: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Debug error: {str(e)}",
#         )


# @router.get("/debug/users", tags=["Debug"])
# async def debug_all_users():
#     """Debug endpoint to list all users (admin only)"""
#     try:
#         result = await auth_service.debug_all_users()
#         return result
#     except Exception as e:
#         logger.error(f"Debug all users error: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Debug error: {str(e)}",
#         )

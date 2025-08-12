from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config.database import get_supabase_admin_client, get_supabase_client
from src.config.settings import get_settings
from src.models.user import UserProfile
from src.utils.exceptions import AppError, AuthenticationError
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()


# Optional security for endpoints that support both authenticated and unauthenticated access
class OptionalHTTPBearer(HTTPBearer):
    def __init__(self, **kwargs):
        super().__init__(auto_error=False, **kwargs)


optional_security = OptionalHTTPBearer()


class AuthService:
    """Authentication service for Supabase Auth integration"""

    def __init__(self):
        self.settings = get_settings()
        self.supabase_client = get_supabase_client()
        self.admin_client = get_supabase_admin_client()

    async def sign_up(self, email: str, password: str) -> dict[str, Any]:
        """Sign up a new user"""
        try:
            logger.info(f"Starting signup process for: {email}")

            response = self.supabase_client.auth.sign_up({"email": email, "password": password})

            logger.info(f"Supabase auth response: {response}")

            if response.user:
                logger.info(f"User created in auth.users with ID: {response.user.id}")

                # Auto-create user profile
                try:
                    await self._create_user_profile(response.user.id, email)
                    logger.info(f"User profile created successfully for: {response.user.id}")
                except Exception as profile_error:
                    logger.error(f"Failed to create user profile: {str(profile_error)}")
                    # Don't fail the signup if profile creation fails

                return {
                    "success": True,
                    "message": "User created successfully. Please check your email for verification.",
                    "user_id": response.user.id,
                    "email": email,
                    "access_token": None,
                    "refresh_token": None,
                    "expires_at": None,
                }
            else:
                logger.error("No user returned from Supabase auth.sign_up")
                raise AuthenticationError("Failed to create user")

        except Exception as e:
            logger.error(f"Sign up failed for {email}: {str(e)}")
            raise AuthenticationError("Sign up failed")

    async def sign_in(self, email: str, password: str) -> dict[str, Any]:
        """Sign in an existing user"""
        try:
            response = self.supabase_client.auth.sign_in_with_password({"email": email, "password": password})

            if response.user and response.session:
                logger.info(f"User signed in successfully: {email}")

                return {
                    "success": True,
                    "message": "Signed in successfully",
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "expires_at": str(response.session.expires_at),
                }
            else:
                raise AuthenticationError("Invalid credentials")

        except Exception as e:
            logger.error(f"Sign in failed for {email}: {str(e)}")
            raise AuthenticationError("Invalid credentials")

    async def sign_out(self, access_token: str) -> dict[str, Any]:
        """Sign out a user"""
        try:
            self.supabase_client.auth.sign_out()
            logger.info("User signed out successfully")

            return {"success": True, "message": "Signed out successfully"}

        except Exception as e:
            logger.error(f"Sign out failed: {str(e)}")
            raise AppError("Sign out failed")

    async def reset_password(self, email: str) -> dict[str, Any]:
        """Send password reset email"""
        try:
            self.supabase_client.auth.reset_password_email(email)
            logger.info(f"Password reset email sent to: {email}")

            return {
                "success": True,
                "message": "Password reset email sent successfully",
            }

        except Exception as e:
            logger.error(f"Password reset failed for {email}: {str(e)}")
            raise AppError("Password reset failed")

    async def get_current_user(self, access_token: str) -> dict[str, Any] | None:
        """Verify the access token with Supabase and return a minimal user dict."""
        try:
            # Use admin client to verify the JWT token
            # The get_user method with access_token parameter verifies the token
            response = self.admin_client.auth.get_user(access_token)
            
            if not response or not response.user:
                logger.warning("Failed to verify access token - no user returned")
                return None

            user = response.user
            user_id = user.id
            email = user.email
            
            if not user_id:
                logger.warning("User ID missing from token response")
                return None

            profile = await self._get_user_profile(user_id)
            logger.info(f"Successfully authenticated user: {user_id}")
            
            return {
                "id": user_id,
                "email": email,
                "profile": profile,
            }
        except Exception as e:
            # Log the specific error for debugging
            logger.warning(f"Token verification failed: {str(e)}")
            return None

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh access token - Simple approach"""
        try:
            # Use Supabase to refresh the token (this part works fine)
            response = self.supabase_client.auth.refresh_session(refresh_token)

            if response.session:
                logger.info("Token refreshed successfully")

                return {
                    "success": True,
                    "message": "Token refreshed successfully",
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "expires_at": str(response.session.expires_at),
                }
            else:
                raise AuthenticationError("Failed to refresh token")

        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise AuthenticationError("Failed to refresh token")

    async def _create_user_profile(self, user_id: str, email: str) -> UserProfile:
        """Create user profile in database"""
        try:
            # Insert into user_profiles table
            response = (
                self.admin_client.table("user_profiles")
                .insert({"id": user_id, "email": email, "full_name": None})
                .execute()
            )

            if response.data:
                logger.info(f"User profile created for: {user_id}")
                return UserProfile(**response.data[0])
            else:
                logger.error(f"No data returned when creating user profile for {user_id}")
                raise Exception("Failed to create user profile - no data returned")

        except Exception as e:
            logger.error(f"Failed to create user profile for {user_id}: {str(e)}")
            raise e

    async def _get_user_profile(self, user_id: str) -> UserProfile | None:
        """Get user profile from database"""
        try:
            response = self.supabase_client.table("user_profiles").select("*").eq("id", user_id).execute()

            if response.data:
                return UserProfile(**response.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get user profile for {user_id}: {str(e)}")
            return None

    # Debug methods (remove in production)
    async def debug_user_by_email(self, email: str) -> dict[str, Any]:
        """Debug method to check user status by email"""
        try:
            # Check user_profiles table
            profile_response = self.admin_client.table("user_profiles").select("*").eq("email", email).execute()

            return {
                "email": email,
                "user_profile": (profile_response.data[0] if profile_response.data else None),
                "profile_exists": len(profile_response.data) > 0,
                "note": "Check Supabase Dashboard > Authentication > Users for auth.users table",
            }

        except Exception as e:
            logger.error(f"Debug user by email failed: {str(e)}")
            return {"error": str(e)}

    async def debug_all_users(self) -> dict[str, Any]:
        """Debug method to list all users (admin only)"""
        try:
            # Get all user profiles
            profiles_response = self.admin_client.table("user_profiles").select("*").execute()

            return {
                "profiles_count": len(profiles_response.data),
                "profiles": profiles_response.data,
                "note": "Check Supabase Dashboard > Authentication > Users for auth.users table",
            }

        except Exception as e:
            logger.error(f"Debug all users failed: {str(e)}")
            return {"error": str(e)}


# Global auth service instance
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Dependency to get current authenticated user"""
    access_token = credentials.credentials

    user = await auth_service.get_current_user(access_token)

    if not user:
        raise AuthenticationError("Invalid authentication credentials")

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
) -> dict[str, Any] | None:
    """Dependency to get current user (optional - doesn't require auth)"""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except AuthenticationError:
        return None

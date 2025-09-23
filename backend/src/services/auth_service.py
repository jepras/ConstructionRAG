from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config.database import get_supabase_admin_client, get_supabase_client
from src.config.settings import get_settings
from src.models.user import UserProfile, UserContext
from src.constants import ANONYMOUS_USER_ID, ANONYMOUS_USERNAME
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
            logger.info("Starting signup process", email=email)

            response = self.supabase_client.auth.sign_up({"email": email, "password": password})

            logger.info("Supabase auth response received", 
                       has_user=bool(response.user),
                       user_id=response.user.id if response.user else None,
                       user_email=response.user.email if response.user else None)

            if response.user:
                logger.info("User created in auth.users", user_id=response.user.id)

                # Auto-create user profile
                try:
                    await self._create_user_profile(response.user.id, email)
                    logger.info("User profile created successfully", user_id=response.user.id)
                except Exception as profile_error:
                    logger.error("Failed to create user profile", 
                               user_id=response.user.id, 
                               error=str(profile_error),
                               error_type=type(profile_error).__name__)
                    # Don't fail the signup if profile creation fails

                logger.info("Signup process completed successfully", 
                           user_id=response.user.id, 
                           email=email)

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
                logger.error("No user returned from Supabase auth.sign_up", email=email)
                raise AuthenticationError("Failed to create user")

        except Exception as e:
            logger.error("Sign up failed", 
                        email=email, 
                        error=str(e),
                        error_type=type(e).__name__)
            raise AuthenticationError("Sign up failed")

    async def sign_in(self, email: str, password: str) -> dict[str, Any]:
        """Sign in an existing user"""
        try:
            logger.info("Starting sign in process", email=email)
            response = self.supabase_client.auth.sign_in_with_password({"email": email, "password": password})
            
            logger.info("Supabase auth response received", 
                       has_user=bool(response.user),
                       has_session=bool(response.session),
                       user_id=response.user.id if response.user else None,
                       user_email=response.user.email if response.user else None)

            if response.user and response.session:
                logger.info("User signed in successfully", 
                           email=email, 
                           user_id=response.user.id,
                           session_expires_at=response.session.expires_at)

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
                logger.error("Sign in failed - missing user or session", 
                           email=email,
                           has_user=bool(response.user),
                           has_session=bool(response.session))
                raise AuthenticationError("Invalid credentials")

        except Exception as e:
            logger.error("Sign in failed with exception", 
                        email=email, 
                        error=str(e),
                        error_type=type(e).__name__)
            raise AuthenticationError("Invalid credentials")

    async def sign_out(self, access_token: str) -> dict[str, Any]:
        """Sign out a user"""
        try:
            self.supabase_client.auth.sign_out()
            logger.info("User signed out successfully")

            return {"success": True, "message": "Signed out successfully"}

        except Exception as e:
            logger.error("Sign out failed", error=str(e))
            raise AppError("Sign out failed")

    async def reset_password(self, email: str) -> dict[str, Any]:
        """Send password reset email"""
        try:
            self.supabase_client.auth.reset_password_email(email)
            logger.info("Password reset email sent", email=email)

            return {
                "success": True,
                "message": "Password reset email sent successfully",
            }

        except Exception as e:
            logger.error("Password reset failed", email=email, error=str(e))
            raise AppError("Password reset failed")

    async def get_current_user_context(self, access_token: str) -> UserContext | None:
        """Verify the access token with Supabase and return UserContext."""
        try:
            # Use admin client to verify the JWT token
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
            if not profile:
                logger.warning("User profile not found", user_id=user_id)
                return None

            logger.debug("Successfully authenticated user", user_id=user_id)

            return UserContext.authenticated(
                user_id=str(user_id),
                username=profile.username,
                email=email or profile.email
            )
        except Exception as e:
            # Log the specific error for debugging
            logger.warning(f"Token verification failed: {str(e)}")
            return None

    async def get_current_user(self, access_token: str) -> dict[str, Any] | None:
        """Legacy method - verify the access token with Supabase and return a minimal user dict."""
        user_context = await self.get_current_user_context(access_token)
        if not user_context:
            return None

        profile = await self._get_user_profile(user_context.id)
        return {
            "id": user_context.id,
            "email": user_context.email,
            "profile": profile,
        }

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
            # Generate username from email prefix
            username = email.split('@')[0].lower() if email else f"user_{str(user_id)[:8]}"

            # Ensure username is unique by checking existing usernames
            existing_response = (
                self.admin_client.table("user_profiles")
                .select("username")
                .eq("username", username)
                .execute()
            )

            # If username exists, append a number
            if existing_response.data:
                counter = 1
                original_username = username
                while existing_response.data:
                    username = f"{original_username}_{counter}"
                    existing_response = (
                        self.admin_client.table("user_profiles")
                        .select("username")
                        .eq("username", username)
                        .execute()
                    )
                    counter += 1

            # Insert into user_profiles table
            response = (
                self.admin_client.table("user_profiles")
                .insert({
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "full_name": None
                })
                .execute()
            )

            if response.data:
                logger.info(f"User profile created for: {user_id} with username: {username}")
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


async def get_user_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserContext:
    """Dependency to get current authenticated user as UserContext"""
    access_token = credentials.credentials

    user_context = await auth_service.get_current_user_context(access_token)

    if not user_context:
        raise AuthenticationError("Invalid authentication credentials")

    return user_context


async def get_user_context_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
) -> UserContext:
    """Dependency to get current user context (returns anonymous if not authenticated)"""
    if not credentials:
        return UserContext.anonymous()

    try:
        user_context = await auth_service.get_current_user_context(credentials.credentials)
        return user_context if user_context else UserContext.anonymous()
    except AuthenticationError:
        return UserContext.anonymous()

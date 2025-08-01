import streamlit as st
from typing import Optional, Dict, Any
from utils.auth_utils import AuthManager, init_auth


def show_login_form() -> Optional[Dict[str, Any]]:
    """Display login form and return auth result"""
    st.markdown("### Sign In")

    with st.form("login_form"):
        email = st.text_input("Email", type="default", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        col1, col2 = st.columns([1, 1])
        with col1:
            submit_button = st.form_submit_button("Sign In", type="primary")
        with col2:
            if st.form_submit_button("Forgot Password?"):
                st.session_state.show_password_reset = True
                st.rerun()

        if submit_button:
            if not email or not password:
                st.error("Please enter both email and password.")
                return None

            init_auth()
            auth_manager = st.session_state.auth_manager
            result = auth_manager.sign_in(email, password)

            if result.get("success"):
                st.success("Signed in successfully!")
                st.rerun()
            else:
                st.error(result.get("message", "Sign in failed."))

            return result

    return None


def show_signup_form() -> Optional[Dict[str, Any]]:
    """Display signup form and return auth result"""
    st.markdown("### Sign Up")

    with st.form("signup_form"):
        email = st.text_input("Email", type="default", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input(
            "Confirm Password", type="password", key="signup_confirm_password"
        )

        submit_button = st.form_submit_button("Sign Up", type="primary")

        if submit_button:
            if not email or not password or not confirm_password:
                st.error("Please fill in all fields.")
                return None

            if password != confirm_password:
                st.error("Passwords do not match.")
                return None

            if len(password) < 6:
                st.error("Password must be at least 6 characters long.")
                return None

            init_auth()
            auth_manager = st.session_state.auth_manager
            result = auth_manager.sign_up(email, password)

            if result.get("success"):
                st.success(
                    "Account created successfully! Please check your email for verification."
                )
                st.info("After verifying your email, you can sign in.")
            else:
                st.error(result.get("message", "Sign up failed."))

            return result

    return None


def show_password_reset_form() -> Optional[Dict[str, Any]]:
    """Display password reset form and return auth result"""
    st.markdown("### Reset Password")
    st.info("Enter your email address and we'll send you a password reset link.")

    with st.form("password_reset_form"):
        email = st.text_input("Email", type="default", key="reset_email")

        col1, col2 = st.columns([1, 1])
        with col1:
            submit_button = st.form_submit_button("Send Reset Link", type="primary")
        with col2:
            if st.form_submit_button("Back to Login"):
                st.session_state.show_password_reset = False
                st.rerun()

        if submit_button:
            if not email:
                st.error("Please enter your email address.")
                return None

            init_auth()
            auth_manager = st.session_state.auth_manager
            result = auth_manager.reset_password(email)

            if result.get("success"):
                st.success("Password reset email sent! Please check your inbox.")
                st.session_state.show_password_reset = False
                st.rerun()
            else:
                st.error(result.get("message", "Password reset failed."))

            return result

    return None


def show_auth_page():
    """Display the main authentication page"""
    st.markdown(
        '<h1 class="main-header">🔐 Authentication</h1>', unsafe_allow_html=True
    )

    # Check if user is already authenticated
    auth_manager = st.session_state.auth_manager
    if auth_manager.is_authenticated():
        st.success("You are already signed in!")
        user_info = auth_manager.get_current_user()
        if user_info and user_info.get("user"):
            user = user_info["user"]
            st.write(f"**Email:** {user.get('email', 'N/A')}")
            st.write(f"**User ID:** {user.get('id', 'N/A')}")

        if st.button("Sign Out"):
            result = auth_manager.sign_out()
            if result.get("success"):
                st.success("Signed out successfully!")
                st.rerun()
            else:
                st.error("Sign out failed.")
        return

    # Show password reset form if requested
    if st.session_state.get("show_password_reset", False):
        show_password_reset_form()
        return

    # Main auth interface
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

    with tab1:
        show_login_form()

    with tab2:
        show_signup_form()


def show_auth_status():
    """Display authentication status in sidebar"""
    auth_manager = st.session_state.auth_manager

    st.markdown("### 🔐 Authentication")

    if auth_manager.is_authenticated():
        user_info = auth_manager.get_current_user()
        if user_info and user_info.get("user"):
            user = user_info["user"]
            st.success(f"✅ Signed in as: {user.get('email', 'N/A')}")

        if st.button("Sign Out", key="sidebar_signout"):
            result = auth_manager.sign_out()
            if result.get("success"):
                st.success("Signed out successfully!")
                st.rerun()
            else:
                st.error("Sign out failed.")
    else:
        st.warning("❌ Not signed in")
        if st.button("Sign In", key="sidebar_signin"):
            st.session_state.current_page = "Authentication"
            st.rerun()


def require_auth_decorator():
    """Decorator to require authentication for pages"""
    init_auth()
    auth_manager = st.session_state.auth_manager

    if not auth_manager.is_authenticated():
        st.error("🔐 Please sign in to access this page.")
        st.info("Use the sidebar to navigate to the Authentication page.")
        st.stop()

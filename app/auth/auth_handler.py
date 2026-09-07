"""
auth_handler.py — login, signup, and session helpers.

Depends on app.db.database (engine/session) and app.db.models (User model),
which are built in the DB batch. Until those exist, this file will import
without errors but calls to login_user()/signup_user() will fail — that's
expected at this stage.
"""

import bcrypt
import streamlit as st

from app.db.database import get_session
from app.db.models import User


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password for storage. Never store plain_password itself."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def signup_user(username: str, plain_password: str, role: str = "consumer") -> tuple[bool, str]:
    """
    Create a new user. Returns (success, message).
    role should be 'consumer', 'seller', or 'admin'.
    """
    if not username or not plain_password:
        return False, "Username and password are required."

    session = get_session()
    try:
        existing = session.query(User).filter_by(username=username).first()
        if existing:
            return False, "That username is already taken."

        new_user = User(
            username=username,
            password_hash=hash_password(plain_password),
            role=role,
        )
        session.add(new_user)
        session.commit()
        return True, "Account created. You can log in now."
    except Exception as e:
        session.rollback()
        return False, f"Signup failed: {e}"
    finally:
        session.close()


def login_user(username: str, plain_password: str) -> tuple[bool, str]:
    """
    Verify credentials and, on success, populate st.session_state.
    Returns (success, message).
    """
    session = get_session()
    try:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return False, "Invalid username or password."

        if not verify_password(plain_password, user.password_hash):
            return False, "Invalid username or password."

        # Populate session state — pages check st.session_state["logged_in"]
        st.session_state["logged_in"] = True
        st.session_state["user_id"] = user.user_id
        st.session_state["username"] = user.username
        st.session_state["role"] = user.role
        return True, f"Welcome back, {user.username}!"
    except Exception as e:
        return False, f"Login failed: {e}"
    finally:
        session.close()


def logout_user() -> None:
    """Clear session state on logout."""
    for key in ("logged_in", "user_id", "username", "role", "persona"):
        st.session_state.pop(key, None)


def require_login() -> bool:
    """
    Call at the top of any protected page. Returns True if logged in,
    otherwise shows a message and returns False so the page can st.stop().
    """
    if not st.session_state.get("logged_in", False):
        st.warning("Please log in first.")
        return False
    return True

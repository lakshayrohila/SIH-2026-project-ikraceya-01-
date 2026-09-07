"""
Home.py — Streamlit entry point.
Run with: streamlit run app/Home.py
"""

import streamlit as st

from app.auth.auth_handler import login_user, signup_user, logout_user

st.set_page_config(page_title="Ikraceya — Compliance Checker", page_icon="✅", layout="wide")

# Initialize session state defaults on first load
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False


def show_login_signup():
    st.title("Ikraceya")
    st.caption("Scan. Verify. Comply.")

    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log In")

            if submitted:
                success, message = login_user(username, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    with tab_signup:
        with st.form("signup_form"):
            new_username = st.text_input("Choose a username", key="signup_username")
            new_password = st.text_input("Choose a password", type="password", key="signup_password")
            role = st.selectbox("I am a...", ["consumer", "seller"], key="signup_role")
            submitted = st.form_submit_button("Sign Up")

            if submitted:
                success, message = signup_user(new_username, new_password, role)
                if success:
                    st.success(message)
                else:
                    st.error(message)


def show_logged_in_home():
    st.title(f"Welcome, {st.session_state['username']}")
    st.write(f"Role: **{st.session_state['role']}**")
    st.write("Use the sidebar to select your persona, then head to the Scan page.")

    if st.button("Log Out"):
        logout_user()
        st.rerun()


# --- Router ---
if st.session_state["logged_in"]:
    show_logged_in_home()
else:
    show_login_signup()

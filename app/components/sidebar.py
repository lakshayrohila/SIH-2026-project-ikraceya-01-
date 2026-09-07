"""
sidebar.py — shared sidebar component.

Call render_sidebar() at the top of every page (after require_login()).
Shows who's logged in, lets them switch persona, and provides logout.
"""

import streamlit as st

from app.auth.auth_handler import logout_user


def render_sidebar():
    with st.sidebar:
        st.markdown("### Ikraceya")
        st.caption("Scan. Verify. Comply.")
        st.divider()

        username = st.session_state.get("username", "Guest")
        role = st.session_state.get("role", "-")
        st.write(f"**User:** {username}")
        st.write(f"**Role:** {role}")

        st.divider()

        current_persona = st.session_state.get("persona", None)
        if current_persona:
            st.write(f"**Active persona:** {current_persona}")
            if st.button("Switch persona"):
                st.session_state.pop("persona", None)
                st.switch_page("pages/1_Persona_Selection.py")
        else:
            st.info("No persona selected yet.")

        st.divider()

        if st.button("Log Out", use_container_width=True):
            logout_user()
            st.switch_page("Home.py")
"""
pages/1_Persona_Selection.py — choose Consumer or Seller/Manufacturer.

This choice is stored in st.session_state["persona"] and read later by the
Results page to tailor how compliance feedback is framed:
  - consumer view: emphasizes rights / what's missing as a buyer
  - seller view: emphasizes mandatory regulatory fixes needed
"""

import streamlit as st

from app.auth.auth_handler import require_login
from app.components.sidebar import render_sidebar

st.set_page_config(page_title="Select Persona — Ikraceya", page_icon="🧭")

if not require_login():
    st.stop()

render_sidebar()

st.title("Who are you scanning as?")
st.write("This changes how we explain the results — pick the one that fits you right now.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🛒 Consumer")
    st.write("I'm checking a product I'm buying or already bought.")
    st.caption("You'll see: what rights you have, what's missing on the label, and how to report issues.")
    if st.button("Continue as Consumer", use_container_width=True):
        st.session_state["persona"] = "consumer"
        st.success("Persona set to Consumer.")
        st.switch_page("pages/2_Scan.py")

with col2:
    st.subheader("🏭 Seller / Manufacturer")
    st.write("I'm checking a product before it goes to market.")
    st.caption("You'll see: exactly which mandatory declarations are missing or wrong, and how to fix them.")
    if st.button("Continue as Seller/Manufacturer", use_container_width=True):
        st.session_state["persona"] = "seller"
        st.success("Persona set to Seller/Manufacturer.")
        st.switch_page("pages/2_Scan.py")
"""
pages/3_Results.py — show compliance results, framed by persona, then log to DB.

Expects st.session_state["scan_result"] to be a dict shaped roughly like:
{
    "overall_status": "COMPLIANT" | "NON_COMPLIANT" | "PARTIAL" | "OUT_OF_SCOPE",
    "extracted_text": "...",
    "checks": [
        {"rule_id": "...", "section": "...", "description": "...",
         "status": "PASS" | "FAIL" | "NOT_APPLICABLE"},
        ...
    ],
}
This shape is produced by app.pipeline.pipeline_runner (later batch) and
consumed here and by app.db.crud.save_scan() (also later batch) for logging.
"""

import streamlit as st

from app.auth.auth_handler import require_login
from app.components.sidebar import render_sidebar

st.set_page_config(page_title="Results — Ikraceya", page_icon="📋")

if not require_login():
    st.stop()

render_sidebar()

st.title("Compliance Results")

if "scan_result" not in st.session_state:
    st.info("No scan yet — head to the Scan page first.")
    st.stop()

result = st.session_state["scan_result"]
persona = st.session_state.get("persona", "consumer")

status = result.get("overall_status", "UNKNOWN")
status_colors = {
    "COMPLIANT": "success",
    "NON_COMPLIANT": "error",
    "PARTIAL": "warning",
    "OUT_OF_SCOPE": "info",
    "PENDING_RULE_ENGINE": "info",
}
getattr(st, status_colors.get(status, "info"))(f"Overall status: **{status}**")

if persona == "consumer":
    st.caption(
        "Shown as a consumer: what's on this label, what's missing, "
        "and what you're entitled to expect."
    )
else:
    st.caption(
        "Shown as a seller/manufacturer: exactly which mandatory "
        "declarations need to be fixed before sale."
    )

st.divider()
st.subheader("Rule-by-rule breakdown")

checks = result.get("checks", [])
if not checks:
    st.write("No individual rule results available yet.")
else:
    for check in checks:
        rule_id = check.get("rule_id", "?")
        section = check.get("section", "")
        description = check.get("description", "")
        check_status = check.get("status", "NOT_APPLICABLE")

        icon = {"PASS": "✅", "FAIL": "❌", "NOT_APPLICABLE": "➖"}.get(check_status, "➖")
        with st.expander(f"{icon} [{rule_id}] {section}"):
            st.write(description)
            st.write(f"**Status:** {check_status}")

st.divider()

with st.expander("Raw extracted text (debug)"):
    st.text(result.get("extracted_text", "(none)"))

# Log this scan once per result, not on every rerun of the page.
if not st.session_state.get("scan_logged", False):
    try:
        from app.db.crud import save_scan

        save_scan(
            user_id=st.session_state["user_id"],
            persona=persona,
            result=result,
        )
        st.session_state["scan_logged"] = True
    except ModuleNotFoundError:
        st.caption("(Scan logging isn't wired up yet — app/db/crud.py comes in a later batch.)")
    except Exception as e:
        st.caption(f"(Could not log this scan: {e})")

if st.button("Scan another item"):
    for key in ("scan_image", "scan_result", "scan_logged"):
        st.session_state.pop(key, None)
    st.switch_page("pages/2_Scan.py")
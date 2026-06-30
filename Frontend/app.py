"""
DMNLight — IHM Streamlit
Point d'entrée unique : lit le query param ?page= et route vers le bon module.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

st.set_page_config(
    page_title="DMNLight",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from components.navbar import render_navbar

# ── Routing ───────────────────────────────────────────────────────────────────
params   = st.query_params
page     = params.get("page", "tables")
table_id = params.get("table_id", None)

render_navbar(page)

# ── Pages ─────────────────────────────────────────────────────────────────────
if page == "home":
    from views.home import render
    render()

elif page == "tables":
    from views.tables import render
    render()

elif page == "detail":
    if table_id:
        from views.table_detail import render
        render(table_id)
    else:
        st.query_params["page"] = "tables"
        st.rerun()

elif page == "new_table":
    from views.new_table import render
    render()

elif page == "manage_rules":
    from views.manage_rules import render
    render(table_id)

elif page == "simulate":
    from views.simulate import render
    render(table_id)

elif page in ("api", "parametres"):
    st.markdown(f"## {page.capitalize()}")
    st.info("Cette section est en cours de développement.")

else:
    st.query_params["page"] = "tables"
    st.rerun()

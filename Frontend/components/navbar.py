import streamlit as st

_TABS = [("Tables", "tables"), ("API", "api"), ("Paramètres", "parametres")]

_TABLE_PAGES = {"tables", "detail", "new_table", "manage_rules", "simulate"}


def render_navbar(current_page: str) -> None:
    active = "tables" if current_page in _TABLE_PAGES else current_page

    tabs_html = ""
    for label, key in _TABS:
        if key == active:
            style = "color:#fff; border-bottom:2px solid #4ade80; padding:0 16px; height:56px; display:flex; align-items:center; font-weight:500; font-size:0.95rem;"
        else:
            style = "color:#8b949e; border-bottom:2px solid transparent; padding:0 16px; height:56px; display:flex; align-items:center; font-size:0.95rem;"
        tabs_html += f'<a href="?page={key}" style="text-decoration:none; {style}">{label}</a>'

    st.markdown(
        f"""
        <style>
        header[data-testid="stHeader"] {{ visibility: hidden; }}
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none !important; }}
        .block-container {{ padding-top: 72px !important; max-width: 100% !important; }}
        div.stButton > button {{
            border-radius: 6px !important;
            padding: 4px 10px !important;
            min-height: 32px !important;
            height: 32px !important;
            font-size: 0.88rem !important;
            border: 1px solid #d1d5db !important;
        }}
        </style>
        <div style="position:fixed; top:0; left:0; width:100%; height:56px;
                    background:#0d1117; z-index:9999; display:flex; align-items:center;
                    padding:0 2rem; box-sizing:border-box; gap:2rem;">
            <span style="color:#fff; font-size:1.2rem; font-weight:700; white-space:nowrap; margin-right:0.5rem;">
                DMN<span style="font-weight:300;">Light</span>
            </span>
            <div style="display:flex; flex:1;">{tabs_html}</div>
            <div style="width:36px; height:36px; background:#7c3aed; border-radius:50%;
                        display:flex; align-items:center; justify-content:center;
                        color:#fff; font-weight:700; font-size:0.8rem; flex-shrink:0;">GP</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

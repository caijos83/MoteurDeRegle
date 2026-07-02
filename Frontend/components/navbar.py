import streamlit as st

_MAIN_TABS = [("Tables", "tables"), ("API", "api")]

_CONTEXT_LABEL = {
    "new_table":    "Nouvelle table",
    "manage_rules": "Édition",
    "detail":       "Détail",
    "simulate":     "Exécution",
}


def render_navbar(current_page: str) -> None:
    context = _CONTEXT_LABEL.get(current_page)

    if context:
        tabs_html = (
            f'<a href="?page=tables" target="_self" class="nav-link">Tables</a>'
            f'<span class="nav-link nav-active">{context}</span>'
        )
    else:
        active = current_page if current_page in dict(_MAIN_TABS) else ("" if current_page == "home" else "tables")
        tabs_html = ""
        for label, key in _MAIN_TABS:
            if key == active:
                tabs_html += f'<span class="nav-link nav-active">{label}</span>'
            else:
                tabs_html += f'<a href="?page={key}" target="_self" class="nav-link">{label}</a>'

    # ── Tout est dans un seul bloc <style> + HTML ──────────────────────────
    # On évite les style= inline complexes sur le div racine qui causent
    # le bug d'affichage Streamlit. On utilise des classes CSS à la place.
    st.markdown(f"""
<style>
/* ── Reset Streamlit ── */
header[data-testid="stHeader"]          {{ visibility: hidden !important; }}
[data-testid="stSidebar"],
[data-testid="collapsedControl"]        {{ display: none !important; }}
.block-container                        {{ padding-top: 72px !important; max-width: 100% !important; }}
#MainMenu, footer                       {{ visibility: hidden !important; }}

/* ── Navbar ── */
.dmn-navbar {{
    position: fixed;
    top: 0; left: 0;
    width: 100%;
    height: 56px;
    background: #ffffff;
    border-bottom: 1.5px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(15,23,42,.04);
    z-index: 9999;
    display: flex;
    align-items: center;
    padding: 0 2rem;
    box-sizing: border-box;
    gap: 2rem;
}}
.dmn-logo {{
    color: #0f172a;
    font-size: 1.2rem;
    font-weight: 800;
    white-space: nowrap;
    margin-right: 0.5rem;
    text-decoration: none;
    letter-spacing: -0.01em;
}}
.dmn-logo span {{ color: #2563eb; font-weight: 700; }}
.dmn-tabs {{
    display: flex;
    flex: 1;
    height: 56px;
    align-items: stretch;
}}
.nav-link {{
    color: #64748b;
    text-decoration: none;
    border-bottom: 2px solid transparent;
    padding: 0 16px;
    height: 56px;
    display: flex;
    align-items: center;
    font-size: 0.95rem;
}}
.nav-link:hover {{
    color: #0f172a;
}}
.nav-active {{
    color: #0f172a !important;
    border-bottom: 2px solid #2563eb !important;
    font-weight: 600;
}}

/* ── Boutons globaux ── */
div.stButton > button {{
    border-radius: 6px !important;
    font-size: 0.88rem !important;
    min-height: 36px !important;
    height: 36px !important;
    padding: 0 14px !important;
}}
</style>

<div class="dmn-navbar">
    <a class="dmn-logo" href="?page=home" target="_self">DMN<span>Light</span></a>
    <div class="dmn-tabs">{tabs_html}</div>
</div>
""", unsafe_allow_html=True)
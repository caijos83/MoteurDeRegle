import streamlit as st
import requests
from utils.api import api_get, policy_badge_html, API_BASE


def render() -> None:
    import time
    result = api_get("/tables")
    if result is None:
        with st.spinner("Connexion à l'API en cours…"):
            time.sleep(1)
        st.rerun()
        return
    tables = result

    # ── Header ────────────────────────────────────────────────────────────────
    col_title, col_btn = st.columns([7, 2])
    with col_title:
        st.markdown(f"## Tables de décision")
        active = len(tables)
        st.caption(f"{active} table{'s' if active != 1 else ''} active{'s' if active != 1 else ''}")
    with col_btn:
        st.markdown("<div style='padding-top:16px;'></div>", unsafe_allow_html=True)
        if st.button("＋  Nouvelle table", use_container_width=True):
            st.query_params["page"] = "new_table"
            st.rerun()

    # ── Filter ────────────────────────────────────────────────────────────────
    col_chk, col_sel = st.columns([0.3, 5])
    with col_chk:
        st.checkbox("Tout sélectionner", key="select_all", label_visibility="collapsed")
    with col_sel:
        policy_filter = st.selectbox(
            "filter",
            ["Toutes les policies", "FIRST", "COLLECT SUM"],
            label_visibility="collapsed",
        )

    if policy_filter != "Toutes les policies":
        tables = [t for t in tables if t.get("hit_policy") == policy_filter]

    if not tables:
        st.info("Aucune table créée pour l'instant.")
        return

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Table header ──────────────────────────────────────────────────────────
    header_style = (
        "background:#f9fafb; padding:10px 8px; font-size:0.78rem; font-weight:600;"
        " color:#6b7280; text-transform:uppercase; letter-spacing:0.05em;"
    )
    hcols = st.columns([4, 2, 1, 1, 2, 2])
    labels = ["Nom de la table", "Hit policy", "Critères", "Règles", "Modifié le", "Actions"]
    for hc, lb in zip(hcols, labels):
        hc.markdown(f'<div style="{header_style}">{lb}</div>', unsafe_allow_html=True)

    # ── Rows ──────────────────────────────────────────────────────────────────
    row_style = "padding:12px 8px; display:flex; align-items:center; border-bottom:1px solid #f3f4f6;"

    for t in tables:
        nb_input  = sum(1 for c in t.get("columns", []) if c["role"] == "input")
        nb_rules  = len(t.get("rules", []))
        modified  = t.get("updated_at", "—")

        rcols = st.columns([4, 2, 1, 1, 2, 2])

        with rcols[0]:
            st.markdown(
                f'<div style="{row_style}"><strong>{t["name"]}</strong></div>',
                unsafe_allow_html=True,
            )
        with rcols[1]:
            st.markdown(
                f'<div style="{row_style}">{policy_badge_html(t["hit_policy"])}</div>',
                unsafe_allow_html=True,
            )
        with rcols[2]:
            st.markdown(f'<div style="{row_style}">{nb_input}</div>', unsafe_allow_html=True)
        with rcols[3]:
            st.markdown(f'<div style="{row_style}">{nb_rules}</div>', unsafe_allow_html=True)
        with rcols[4]:
            st.markdown(f'<div style="{row_style}">{modified}</div>', unsafe_allow_html=True)
        with rcols[5]:
            a1, a2, a3 = st.columns(3)
            with a1:
                if st.button("✎", key=f"edit_{t['id']}", help="Voir le détail"):
                    st.query_params["page"] = "detail"
                    st.query_params["table_id"] = t["id"]
                    st.rerun()
            with a2:
                if st.button("▶", key=f"run_{t['id']}", help="Simuler"):
                    st.query_params["page"] = "simulate"
                    st.query_params["table_id"] = t["id"]
                    st.rerun()
            with a3:
                if st.button("🗑", key=f"del_{t['id']}", help="Supprimer"):
                    requests.delete(f"{API_BASE}/tables/{t['id']}", timeout=5)
                    st.rerun()

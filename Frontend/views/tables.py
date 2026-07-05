import json
import streamlit as st
import requests
from html import escape as _esc
from utils.api import api_get, policy_badge_html, fmt_date, API_BASE

_COL_WIDTHS = [0.35, 3.65, 2, 1, 1, 2, 2]


def render() -> None:
    import time
    result = api_get("/tables")
    if result is None:
        with st.spinner("Connexion à l'API en cours…"):
            time.sleep(1)
        st.rerun()
        return
    tables = result

    st.markdown(
        "<style>div[data-testid='stCheckbox']{padding-top:10px;}</style>",
        unsafe_allow_html=True,
    )

    # ── Filtre (persistant via session_state, lu avant le widget) ──────────────
    policy_filter = st.session_state.get("policy_filter", "Toutes les policies")
    if policy_filter != "Toutes les policies":
        tables = [t for t in tables if t.get("hit_policy") == policy_filter]

    selected_ids = [t["id"] for t in tables if st.session_state.get(f"chk_{t['id']}", False)]

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

    # ── Barre d'actions groupées ─────────────────────────────────────────────────
    if selected_ids:
        selected_tables = [t for t in tables if t["id"] in selected_ids]
        n = len(selected_ids)
        bar_l, bar_r = st.columns([5, 4])
        with bar_l:
            st.markdown(
                f"<div style='padding-top:10px; font-size:0.92rem; color:#0f172a;'>"
                f"<strong>{n}</strong> table{'s' if n != 1 else ''} sélectionnée{'s' if n != 1 else ''}</div>",
                unsafe_allow_html=True,
            )
        with bar_r:
            be1, be2 = st.columns(2)
            with be1:
                st.download_button(
                    "⤓  Exporter",
                    data=json.dumps(selected_tables, indent=2, ensure_ascii=False),
                    file_name="tables_export.json",
                    mime="application/json",
                    use_container_width=True,
                    key="bulk_export",
                )
            with be2:
                if st.button("🗑  Supprimer", use_container_width=True, key="bulk_delete_btn"):
                    st.session_state["confirm_bulk_delete"] = True

        if st.session_state.get("confirm_bulk_delete"):
            st.warning(f"Supprimer définitivement {n} table{'s' if n != 1 else ''} ? Cette action est irréversible.")
            cc1, cc2, _ = st.columns([1, 1, 4])
            with cc1:
                if st.button("Confirmer", type="primary", key="confirm_del_yes"):
                    for tid in selected_ids:
                        requests.delete(f"{API_BASE}/tables/{tid}", timeout=5)
                        st.session_state.pop(f"chk_{tid}", None)
                    st.session_state["confirm_bulk_delete"] = False
                    st.session_state["select_all"] = False
                    st.rerun()
            with cc2:
                if st.button("Annuler", key="confirm_del_no"):
                    st.session_state["confirm_bulk_delete"] = False
                    st.rerun()

    # ── Sélection globale / filtre ───────────────────────────────────────────────
    def _toggle_all():
        val = st.session_state["select_all"]
        for t in tables:
            st.session_state[f"chk_{t['id']}"] = val

    col_chk, col_sel = st.columns([0.3, 5])
    with col_chk:
        st.checkbox(
            "Tout sélectionner", key="select_all",
            label_visibility="collapsed", on_change=_toggle_all,
        )
    with col_sel:
        st.selectbox(
            "filter",
            ["Toutes les policies", "FIRST", "COLLECT SUM"],
            key="policy_filter",
            label_visibility="collapsed",
        )

    if not tables:
        st.info("Aucune table créée pour l'instant.")
        return

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Table header ──────────────────────────────────────────────────────────
    header_style = (
        "background:#f9fafb; padding:10px 8px; font-size:0.78rem; font-weight:600;"
        " color:#6b7280; text-transform:uppercase; letter-spacing:0.05em;"
    )
    hcols = st.columns(_COL_WIDTHS)
    labels = ["", "Nom de la table", "Hit policy", "Critères", "Règles", "Modifié le", "Actions"]
    for hc, lb in zip(hcols, labels):
        hc.markdown(f'<div style="{header_style}">{lb}</div>', unsafe_allow_html=True)

    # ── Rows ──────────────────────────────────────────────────────────────────
    row_style = "padding:12px 8px; display:flex; align-items:center; border-bottom:1px solid #f3f4f6;"

    for t in tables:
        nb_input  = sum(1 for c in t.get("columns", []) if c["role"] == "input")
        nb_rules  = len(t.get("rules", []))
        modified  = fmt_date(t.get("updated_at"))

        rcols = st.columns(_COL_WIDTHS)

        with rcols[0]:
            st.checkbox("", key=f"chk_{t['id']}", label_visibility="collapsed")
        with rcols[1]:
            st.markdown(
                f'<div style="{row_style}"><strong>{_esc(t["name"])}</strong></div>',
                unsafe_allow_html=True,
            )
        with rcols[2]:
            st.markdown(
                f'<div style="{row_style}">{policy_badge_html(t["hit_policy"])}</div>',
                unsafe_allow_html=True,
            )
        with rcols[3]:
            st.markdown(f'<div style="{row_style}">{nb_input}</div>', unsafe_allow_html=True)
        with rcols[4]:
            st.markdown(f'<div style="{row_style}">{nb_rules}</div>', unsafe_allow_html=True)
        with rcols[5]:
            st.markdown(f'<div style="{row_style}">{modified}</div>', unsafe_allow_html=True)
        with rcols[6]:
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
                if st.button("✕", key=f"del_{t['id']}", help="Supprimer"):
                    st.session_state["confirm_single_delete"] = t["id"]
                    st.rerun()

    # ── Confirmation suppression individuelle ─────────────────────────────────
    pending_id = st.session_state.get("confirm_single_delete")
    if pending_id:
        pending_table = next((t for t in tables if t["id"] == pending_id), None)
        name = pending_table["name"] if pending_table else pending_id
        st.warning(f'Supprimer définitivement la table **{name}** ? Cette action est irréversible.')
        cd1, cd2, _ = st.columns([1, 1, 4])
        with cd1:
            if st.button("Confirmer", type="primary", key="confirm_single_yes"):
                requests.delete(f"{API_BASE}/tables/{pending_id}", timeout=5)
                st.session_state.pop(f"chk_{pending_id}", None)
                st.session_state.pop("confirm_single_delete", None)
                st.rerun()
        with cd2:
            if st.button("Annuler", key="confirm_single_no"):
                st.session_state.pop("confirm_single_delete", None)
                st.rerun()

import json
import streamlit as st
import requests
from utils.api import api_get, policy_badge_html, fmt_condition, fmt_output_html, score_range, API_BASE


def _rules_table_html(table: dict) -> str:
    input_cols  = [c for c in table["columns"] if c["role"] == "input"]
    output_cols = [c for c in table["columns"] if c["role"] == "output"]
    rules       = table.get("rules", [])

    th_base = "padding:10px 14px; font-size:0.85rem; font-weight:600; color:#fff; text-align:left;"
    td_base = "padding:10px 14px; border-bottom:1px solid #f0f0f0; font-size:0.9rem;"

    # Header
    header = f'<th style="{th_base} background:#1e293b; width:40px; text-align:center;">#</th>'
    for c in input_cols:
        header += f'<th style="{th_base} background:#4c3888;">{c["name"]}</th>'
    for c in output_cols:
        header += f'<th style="{th_base} background:#15803d;">{c["name"]}</th>'

    # Rows
    rows_html = ""
    for idx, rule in enumerate(rules, start=1):
        row = f'<td style="{td_base} text-align:center; color:#9ca3af;">{idx}</td>'
        for c in input_cols:
            raw = rule.get("conditions", {}).get(c["name"], "—")
            row += f'<td style="{td_base}">{fmt_condition(raw)}</td>'
        for c in output_cols:
            val = rule.get("output", {}).get(c["name"], "—")
            row += f'<td style="{td_base}">{fmt_output_html(val)}</td>'
        bg = "#ffffff" if idx % 2 == 1 else "#fafafa"
        rows_html += f'<tr style="background:{bg};">{row}</tr>'

    return (
        '<div style="overflow-x:auto; border:1px solid #e5e7eb; border-radius:8px; margin-top:8px;">'
        '<table style="width:100%; border-collapse:collapse;">'
        f'<thead><tr>{header}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        "</table></div>"
    )


def render(table_id: str) -> None:
    table = api_get(f"/tables/{table_id}")
    if not table:
        st.error("Table introuvable.")
        if st.button("← Retour"):
            st.query_params.clear()
            st.query_params["page"] = "tables"
            st.rerun()
        return

    input_cols  = [c for c in table["columns"] if c["role"] == "input"]
    output_cols = [c for c in table["columns"] if c["role"] == "output"]
    rules       = table.get("rules", [])
    modified    = table.get("updated_at", "—")

    # ── Breadcrumb ────────────────────────────────────────────────────────────
    st.markdown(
        f'<p style="font-size:0.9rem; color:#6b7280; margin-bottom:4px;">'
        f'<a href="?page=tables" target="_self" style="color:#4f46e5; text-decoration:none;">Tables</a>'
        f' &rsaquo; {table["name"]}</p>',
        unsafe_allow_html=True,
    )

    # ── Title row ─────────────────────────────────────────────────────────────
    col_title, col_btns = st.columns([6, 2])
    with col_title:
        st.markdown(f"## {table['name']}")
        st.markdown(
            f'{policy_badge_html(table["hit_policy"])}'
            f'  <span style="color:#6b7280; font-size:0.88rem;">Modifié le {modified}</span>',
            unsafe_allow_html=True,
        )
    with col_btns:
        st.markdown("<div style='padding-top:16px;'></div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("✎  Modifier", use_container_width=True):
                st.query_params["page"] = "manage_rules"
                st.query_params["table_id"] = table_id
                st.rerun()
        with b2:
            if st.button("▶  Exécuter", use_container_width=True):
                st.query_params["page"] = "simulate"
                st.query_params["table_id"] = table_id
                st.rerun()

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # ── Stat cards ────────────────────────────────────────────────────────────
    card_css = (
        "background:#f9fafb; border-radius:8px; padding:20px 16px;"
        " text-align:center; border:1px solid #e5e7eb;"
    )
    c1, c2, c3, c4 = st.columns(4)
    stats = [
        (str(len(input_cols)),   "Critères d'entrée"),
        (str(len(output_cols)),  "Sortie"),
        (str(len(rules)),        "Règles définies"),
        (score_range(table),     "Plage de score"),
    ]
    for col, (value, label) in zip([c1, c2, c3, c4], stats):
        col.markdown(
            f'<div style="{card_css}">'
            f'<div style="font-size:1.8rem; font-weight:700; color:#111827;">{value}</div>'
            f'<div style="font-size:0.82rem; color:#6b7280; margin-top:4px;">{label}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_regles, tab_json, tab_hist = st.tabs(["Règles", "JSON", "Historique"])

    with tab_regles:
        if not rules:
            st.info("Aucune règle définie.")
        else:
            st.markdown(_rules_table_html(table), unsafe_allow_html=True)

    with tab_json:
        st.code(json.dumps(table, indent=2, ensure_ascii=False), language="json")

    with tab_hist:
        st.info("Historique non disponible dans cette version.")

    # ── Delete zone ───────────────────────────────────────────────────────────
    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
    with st.expander("Zone dangereuse"):
        if st.button("🗑️ Supprimer cette table", type="primary"):
            requests.delete(f"{API_BASE}/tables/{table_id}", timeout=5)
            st.query_params.clear()
            st.query_params["page"] = "tables"
            st.rerun()

import streamlit as st
import requests
from utils.api import api_get, policy_badge_html, fmt_condition, fmt_output_html, condition_form, API_BASE


def render(table_id: str | None = None) -> None:
    tables = api_get("/tables") or []
    if not tables:
        st.info("Aucune table disponible.")
        return

    # ── Table selector ────────────────────────────────────────────────────────
    table_map = {t["name"]: t for t in tables}
    default_idx = 0
    if table_id:
        names = list(table_map.keys())
        for i, t in enumerate(tables):
            if t["id"] == table_id:
                default_idx = i
                break

    selected_name = st.selectbox("Table", list(table_map.keys()), index=default_idx)
    table = table_map[selected_name]

    input_cols  = [c for c in table["columns"] if c["role"] == "input"]
    output_cols = [c for c in table["columns"] if c["role"] == "output"]
    rules = table.get("rules", [])

    # ── Breadcrumb ────────────────────────────────────────────────────────────
    st.markdown(
        f'<p style="font-size:0.9rem; color:#6b7280;">'
        f'<a href="?page=tables" style="color:#4f46e5; text-decoration:none;">Tables</a>'
        f' &rsaquo; <a href="?page=detail&table_id={table["id"]}" style="color:#4f46e5; text-decoration:none;">{table["name"]}</a>'
        f" &rsaquo; Gérer les règles</p>",
        unsafe_allow_html=True,
    )

    col_h, col_b = st.columns([6, 2])
    with col_h:
        st.markdown(f"## {table['name']}")
        st.markdown(policy_badge_html(table["hit_policy"]), unsafe_allow_html=True)
    with col_b:
        st.markdown("<div style='padding-top:16px;'></div>", unsafe_allow_html=True)
        if st.button("▶  Exécuter", use_container_width=True):
            st.query_params["page"] = "simulate"
            st.query_params["table_id"] = table["id"]
            st.rerun()

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # ── Existing rules ────────────────────────────────────────────────────────
    if not rules:
        st.info("Aucune règle. Ajoutez-en une ci-dessous.")
    else:
        th = "padding:8px 10px; font-size:0.8rem; font-weight:600; color:#fff; text-align:left;"
        td = "padding:9px 10px; border-bottom:1px solid #f0f0f0; font-size:0.88rem;"

        header = f'<th style="{th} background:#1e293b; width:32px; text-align:center;">#</th>'
        for c in input_cols:
            header += f'<th style="{th} background:#4c3888;">{c["name"]}</th>'
        for c in output_cols:
            header += f'<th style="{th} background:#15803d;">{c["name"]}</th>'
        header += f'<th style="{th} background:#374151;">Action</th>'

        rows_html = ""
        for idx, rule in enumerate(rules, start=1):
            row = f'<td style="{td} text-align:center; color:#9ca3af;">{idx}</td>'
            for c in input_cols:
                raw = rule.get("conditions", {}).get(c["name"], "—")
                row += f'<td style="{td}">{fmt_condition(raw)}</td>'
            for c in output_cols:
                val = rule.get("output", {}).get(c["name"], "—")
                row += f'<td style="{td}">{fmt_output_html(val)}</td>'
            row += f'<td style="{td}">_BTN_{idx}_</td>'
            rows_html += f'<tr style="background:{"#fff" if idx%2 else "#fafafa"}">{row}</tr>'

        # Render table without action column (actions handled by buttons below)
        header_no_action = f'<th style="{th} background:#1e293b; width:32px; text-align:center;">#</th>'
        for c in input_cols:
            header_no_action += f'<th style="{th} background:#4c3888;">{c["name"]}</th>'
        for c in output_cols:
            header_no_action += f'<th style="{th} background:#15803d;">{c["name"]}</th>'

        rows_no_action = ""
        for idx, rule in enumerate(rules, start=1):
            row = f'<td style="{td} text-align:center; color:#9ca3af;">{idx}</td>'
            for c in input_cols:
                raw = rule.get("conditions", {}).get(c["name"], "—")
                row += f'<td style="{td}">{fmt_condition(raw)}</td>'
            for c in output_cols:
                val = rule.get("output", {}).get(c["name"], "—")
                row += f'<td style="{td}">{fmt_output_html(val)}</td>'
            rows_no_action += f'<tr style="background:{"#fff" if idx%2 else "#fafafa"}">{row}</tr>'

        st.markdown(
            f'<div style="overflow-x:auto; border:1px solid #e5e7eb; border-radius:8px;">'
            f'<table style="width:100%; border-collapse:collapse;">'
            f'<thead><tr>{header_no_action}</tr></thead>'
            f'<tbody>{rows_no_action}</tbody>'
            f"</table></div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        for r_idx, rule in enumerate(rules):
            if st.button(f"🗑️ Supprimer règle {r_idx+1}", key=f"del_rule_{r_idx}"):
                new_rules = [r for i, r in enumerate(rules) if i != r_idx]
                requests.put(f"{API_BASE}/tables/{table['id']}", json={"rules": new_rules}, timeout=5)
                st.rerun()

    # ── Add rule form ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Ajouter une règle")

    with st.form("add_rule", border=True):
        conditions: dict = {}
        outputs_vals: dict = {}

        if input_cols:
            st.markdown("**Conditions**")
            for col in input_cols:
                st.markdown(f"*{col['name']}*")
                skip = st.checkbox("Sans condition (toujours vrai)", key=f"skip_{col['name']}")
                if not skip:
                    cond = condition_form(col, key_prefix=f"cond_{col['name']}")
                    conditions[col["name"]] = cond

        st.divider()
        st.markdown("**Résultats si la règle s'applique**")
        for col in output_cols:
            if col["type"] == "number":
                val = st.number_input(col["name"], key=f"out_{col['name']}", step=1.0)
                outputs_vals[col["name"]] = str(int(val) if val == int(val) else val)
            elif col["type"] == "boolean":
                val = st.selectbox(col["name"], ["Vrai", "Faux"], key=f"out_{col['name']}")
                outputs_vals[col["name"]] = "true" if val == "Vrai" else "false"
            else:
                val = st.text_input(col["name"], key=f"out_{col['name']}")
                outputs_vals[col["name"]] = val

        if st.form_submit_button("Ajouter la règle", use_container_width=True, type="primary"):
            if not all(str(v).strip() for v in outputs_vals.values()):
                st.error("Veuillez renseigner tous les résultats.")
            else:
                new_rule = {"conditions": conditions, "output": outputs_vals}
                resp = requests.put(
                    f"{API_BASE}/tables/{table['id']}",
                    json={"rules": rules + [new_rule]},
                    timeout=5,
                )
                if resp.ok:
                    st.success("Règle ajoutée.")
                    st.rerun()
                else:
                    st.error("Erreur lors de l'ajout.")

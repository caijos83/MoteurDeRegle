import json
import streamlit as st
import requests
from utils.api import (
    api_get, policy_badge_html, condition_form, API_BASE,
)

_TYPE_FR = {"number": "numérique", "text": "texte", "boolean": "booléen"}

_TABLE_CSS = """
<style>
.rules-wrapper [data-testid="stHorizontalBlock"] {
    gap: 0 !important;
    margin-bottom: 0 !important;
    align-items: center !important;
}
.rules-wrapper [data-testid="column"] > div {
    padding-bottom: 0 !important;
    margin-bottom: 0 !important;
}
/* Champs de saisie dans le tableau */
.rules-wrapper [data-testid="stTextInput"] > div > div > input {
    border-top: none !important;
    border-left: none !important;
    border-right: none !important;
    border-bottom: 1px solid #f0f0f0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    padding: 10px 12px !important;
    font-size: 0.9rem !important;
    min-height: 43px !important;
    box-shadow: none !important;
}
.rules-wrapper [data-testid="stTextInput"] > div > div > input:focus {
    border-bottom: 1px solid #4f46e5 !important;
    box-shadow: none !important;
}
.rules-wrapper [data-testid="stTextInput"] {
    margin: 0 !important;
    padding: 0 !important;
}
/* Bouton 🗑 */
.rules-wrapper div.stButton > button {
    border: none !important;
    border-bottom: 1px solid #f0f0f0 !important;
    border-radius: 0 !important;
    background: #fafafa !important;
    color: #d1d5db !important;
    min-height: 43px !important;
    height: 43px !important;
    width: 100% !important;
    font-size: 1rem !important;
    padding: 0 !important;
    margin: 0 !important;
}
.rules-wrapper div.stButton > button:hover {
    background: #fee2e2 !important;
    color: #dc2626 !important;
}
</style>
"""


def _cell(content: str, bg: str, height: str = "38px", align: str = "left") -> str:
    return (
        f'<div style="background:{bg}; height:{height}; padding:0 12px;'
        f' display:flex; align-items:center; text-align:{align}; box-sizing:border-box;">'
        f"{content}</div>"
    )


def _save_rules(table_id: str, rules: list) -> None:
    requests.put(f"{API_BASE}/tables/{table_id}", json={"rules": rules}, timeout=5)


def _reset_edit_state(table_id: str) -> None:
    if st.session_state.get("_current_table_id") != table_id:
        for key in list(st.session_state.keys()):
            if key.startswith("cond_") or key.startswith("out_"):
                del st.session_state[key]
        st.session_state["_current_table_id"] = table_id


def render(table_id: str | None = None) -> None:
    tables = api_get("/tables") or []
    if not tables:
        st.info("Aucune table disponible.")
        return

    table_map = {t["name"]: t for t in tables}
    default_idx = 0
    if table_id:
        for i, t in enumerate(tables):
            if t["id"] == table_id:
                default_idx = i
                break
    default_idx = min(default_idx, len(table_map) - 1)

    selected_name = st.selectbox(
        "Table", list(table_map.keys()), index=default_idx,
        key="table_selector", label_visibility="collapsed",
    )
    table = table_map[selected_name]
    _reset_edit_state(table["id"])

    input_cols  = [c for c in table["columns"] if c["role"] == "input"]
    output_cols = [c for c in table["columns"] if c["role"] == "output"]
    rules = table.get("rules", [])

    # ── Breadcrumb ────────────────────────────────────────────────────────────
    st.markdown(
        f'<p style="font-size:0.9rem; color:#6b7280; margin-bottom:4px;">'
        f'<a href="?page=tables" target="_self" style="color:#4f46e5; text-decoration:none;">Tables</a>'
        f' &rsaquo; <a href="?page=detail&table_id={table["id"]}" target="_self" style="color:#4f46e5; text-decoration:none;">'
        f'{table["name"]}</a> &rsaquo; Règles</p>',
        unsafe_allow_html=True,
    )

    # ── En-tête page ──────────────────────────────────────────────────────────
    col_h, col_btns = st.columns([5, 4])
    with col_h:
        st.markdown(f"## {table['name']}")
        nb = len(input_cols)
        st.markdown(
            f"{policy_badge_html(table['hit_policy'])}"
            f'&nbsp;<span style="color:#6b7280; font-size:0.88rem;">'
            f"{nb} critère{'s' if nb != 1 else ''} · {len(rules)} règle{'s' if len(rules) != 1 else ''}</span>",
            unsafe_allow_html=True,
        )
    with col_btns:
        st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
        b1, b2, b3 = st.columns(3)
        with b1:
            st.download_button(
                "↓ Export JSON",
                data=json.dumps(table, indent=2, ensure_ascii=False),
                file_name=f"{table['name']}.json",
                mime="application/json",
                use_container_width=True,
            )
        with b2:
            show_import = st.button("↑ Import", use_container_width=True)
        with b3:
            save_clicked = st.button("✓  Enregistrer", use_container_width=True, type="primary")

    if show_import:
        uploaded = st.file_uploader("Fichier JSON de règles", type="json")
        if uploaded:
            try:
                data = json.loads(uploaded.read())
                new_rules = data.get("rules", data) if isinstance(data, dict) else data
                resp = requests.put(
                    f"{API_BASE}/tables/{table['id']}",
                    json={"rules": rules + new_rules}, timeout=5,
                )
                if resp.ok:
                    st.success(f"{len(new_rules)} règle(s) importée(s).")
                    st.rerun()
            except Exception as e:
                st.error(f"Fichier invalide : {e}")

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

    if not input_cols and not output_cols:
        st.info("Cette table n'a pas de colonnes.")
        return

    n = len(input_cols) + len(output_cols)
    col_widths = [0.5] + [2.5] * n + [0.6]

    st.markdown(_TABLE_CSS + '<div class="rules-wrapper">', unsafe_allow_html=True)

    # ── En-tête noms ─────────────────────────────────────────────────────────
    h_row = st.columns(col_widths)
    h_row[0].markdown(_cell("#", "#1e293b", align="center"), unsafe_allow_html=True)
    for i, c in enumerate(input_cols):
        h_row[i + 1].markdown(
            _cell(f"<span style='font-size:.83rem; font-weight:600; color:#fff;'>{c['name']}</span>", "#4c3888"),
            unsafe_allow_html=True,
        )
    for i, c in enumerate(output_cols):
        h_row[len(input_cols) + 1 + i].markdown(
            _cell(f"<span style='font-size:.83rem; font-weight:600; color:#fff;'>{c['name']}</span>", "#15803d"),
            unsafe_allow_html=True,
        )
    h_row[-1].markdown(_cell("", "#374151"), unsafe_allow_html=True)

    # ── En-tête types ─────────────────────────────────────────────────────────
    t_row = st.columns(col_widths)
    t_row[0].markdown(_cell("", "#1e293b", height="24px"), unsafe_allow_html=True)
    for i, c in enumerate(input_cols):
        t_row[i + 1].markdown(
            _cell(f"<span style='font-size:.74rem; color:#d1d5db;'>{_TYPE_FR.get(c['type'])}</span>", "#4c3888", height="24px"),
            unsafe_allow_html=True,
        )
    for i, c in enumerate(output_cols):
        t_row[len(input_cols) + 1 + i].markdown(
            _cell(f"<span style='font-size:.74rem; color:#d1d5db;'>{_TYPE_FR.get(c['type'])}</span>", "#15803d", height="24px"),
            unsafe_allow_html=True,
        )
    t_row[-1].markdown(_cell("", "#374151", height="24px"), unsafe_allow_html=True)

    # ── Lignes éditables ──────────────────────────────────────────────────────
    for idx, rule in enumerate(rules, start=1):
        d_row = st.columns(col_widths)

        d_row[0].markdown(
            f'<div style="padding:0 12px; color:#9ca3af; font-size:.88rem; '
            f'height:43px; display:flex; align-items:center; border-bottom:1px solid #f0f0f0;">{idx}</div>',
            unsafe_allow_html=True,
        )

        for i, c in enumerate(input_cols):
            with d_row[i + 1]:
                current = rule.get("conditions", {}).get(c["name"], "")
                if current == "—":
                    current = ""
                st.text_input(
                    c["name"], value=current,
                    key=f"cond_{idx}_{c['name']}",
                    placeholder="— (ignorer)",
                    label_visibility="collapsed",
                )

        for i, c in enumerate(output_cols):
            with d_row[len(input_cols) + 1 + i]:
                current = str(rule.get("output", {}).get(c["name"], ""))
                st.text_input(
                    c["name"], value=current,
                    key=f"out_{idx}_{c['name']}",
                    label_visibility="collapsed",
                )

        with d_row[-1]:
            if st.button("🗑", key=f"del_{idx - 1}"):
                _save_rules(table["id"], [r for j, r in enumerate(rules) if j != idx - 1])
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Sauvegarde de toutes les règles ───────────────────────────────────────
    if save_clicked:
        updated_rules = []
        for idx, rule in enumerate(rules, start=1):
            conditions = {}
            for c in input_cols:
                val = str(st.session_state.get(f"cond_{idx}_{c['name']}", "")).strip()
                if val:
                    conditions[c["name"]] = val
            outputs = {}
            for c in output_cols:
                val = str(st.session_state.get(f"out_{idx}_{c['name']}", ""))
                outputs[c["name"]] = val
            updated_rules.append({"conditions": conditions, "output": outputs})
        _save_rules(table["id"], updated_rules)
        st.toast("Table à jour !", icon="✅")

    # ── Ajouter une règle ─────────────────────────────────────────────────────
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    if st.button("＋  Ajouter une règle", use_container_width=True):
        st.session_state["show_add_rule"] = not st.session_state.get("show_add_rule", False)
        st.rerun()

    if st.session_state.get("show_add_rule"):
        with st.form("add_rule_form", border=True):
            st.markdown("**Conditions** *(vide = toujours vrai)*")
            form_cols = st.columns(len(input_cols)) if input_cols else []
            conditions: dict = {}
            for fc, col in zip(form_cols, input_cols):
                with fc:
                    st.markdown(f"*{col['name']}*")
                    conditions[col["name"]] = condition_form(col, f"ar_{col['name']}")

            if output_cols:
                st.divider()
                st.markdown("**Résultats**")
            outputs_vals: dict = {}
            out_cols_form = st.columns(len(output_cols)) if output_cols else []
            for fc, col in zip(out_cols_form, output_cols):
                with fc:
                    if col["type"] == "number":
                        v = st.number_input(col["name"], key=f"ar_out_{col['name']}", step=1.0)
                        outputs_vals[col["name"]] = str(int(v) if v == int(v) else v)
                    elif col["type"] == "boolean":
                        v = st.selectbox(col["name"], ["true", "false"], key=f"ar_out_{col['name']}")
                        outputs_vals[col["name"]] = v
                    else:
                        v = st.text_input(col["name"], key=f"ar_out_{col['name']}")
                        outputs_vals[col["name"]] = v

            if st.form_submit_button("Ajouter la règle", use_container_width=True, type="primary"):
                clean_cond = {k: v for k, v in conditions.items() if v and str(v).strip()}
                if not all(str(v).strip() for v in outputs_vals.values()):
                    st.error("Renseignez tous les résultats.")
                else:
                    requests.put(
                        f"{API_BASE}/tables/{table['id']}",
                        json={"rules": rules + [{"conditions": clean_cond, "output": outputs_vals}]},
                        timeout=5,
                    )
                    st.session_state["show_add_rule"] = False
                    st.rerun()

    st.markdown(
        '<p style="font-size:0.78rem; color:#9ca3af; margin-top:10px;">'
        "Opérateurs supportés : <code>&gt;</code> <code>&lt;</code> <code>=</code>"
        " <code>!=</code> <code>[a..b]</code> <code>liste</code>"
        " · Utilisez <code>—</code> pour ignorer un critère</p>",
        unsafe_allow_html=True,
    )

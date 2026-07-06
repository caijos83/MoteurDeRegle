"""
Vue édition des règles d'une table — tableau de règles entièrement éditable
avec ajout/suppression de colonnes et de règles, import/export JSON et sauvegarde via API.
"""

import json
import streamlit as st
import requests
from html import escape as _esc
from utils.api import (
    api_get, policy_badge_html, condition_form, API_BASE,
)

_TYPE_FR = {"number": "numérique", "text": "texte", "boolean": "booléen"}
_TYPE_LABELS = ["numérique", "texte", "booléen"]
_TYPE_TO_API = {"numérique": "number", "texte": "text", "booléen": "boolean"}

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
    border-bottom: 1px solid #4c8c6b !important;
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
    """
    Retourne le HTML d'une cellule de tableau (en-tête ou données).
    Entrées : content — HTML interne, bg — couleur de fond, height, align.
    Retour : chaîne HTML de la cellule.
    """
    return (
        f'<div style="background:{bg}; height:{height}; padding:0 12px;'
        f' display:flex; align-items:center; text-align:{align}; box-sizing:border-box;">'
        f"{content}</div>"
    )


def _save_rules(table_id: str, rules: list) -> None:
    """
    Envoie la liste de règles à l'API via PUT /tables/{table_id}.
    Entrées : table_id — UUID de la table, rules — liste de règles à persister.
    """
    requests.put(f"{API_BASE}/tables/{table_id}", json={"rules": rules}, timeout=5)


def _reset_edit_state(table_id: str) -> None:
    """
    Vide les clés cond_* et out_* du session_state quand on change de table,
    évitant de mélanger les saisies d'une table à l'autre.
    Entrée : table_id — UUID de la table actuellement sélectionnée.
    """
    if st.session_state.get("_current_table_id") != table_id:
        for key in list(st.session_state.keys()):
            if key.startswith("cond_") or key.startswith("out_"):
                del st.session_state[key]
        st.session_state["_current_table_id"] = table_id
        st.session_state["mr_show_import"] = False


def _init_state() -> None:
    """Initialise les clés de session_state propres à cette page si elles sont absentes."""
    for k, v in [("mr_show_import", False), ("mr_upload_key", 0)]:
        if k not in st.session_state:
            st.session_state[k] = v


def _add_column_popover(table: dict, role: str, key_prefix: str) -> None:
    """
    Affiche un popover d'ajout de colonne et envoie le PUT si l'utilisateur confirme.
    Entrées : table — dict de la table courante, role — "input" ou "output",
              key_prefix — préfixe unique pour les clés Streamlit.
    """
    label = "Nouvelle entrée (IN)" if role == "input" else "Nouvelle sortie (OUT)"
    with st.popover("➕", use_container_width=True, help=f"Ajouter une colonne {'IN' if role == 'input' else 'OUT'}"):
        st.markdown(f"**{label}**")
        nm = st.text_input("Nom", key=f"{key_prefix}_name", label_visibility="collapsed",
                            placeholder="Nom de la colonne")
        tp = st.selectbox("Type", _TYPE_LABELS, key=f"{key_prefix}_type", label_visibility="collapsed")
        if st.button("Ajouter", key=f"{key_prefix}_add", use_container_width=True, type="primary"):
            name_clean = nm.strip()
            if not name_clean:
                st.warning("Donnez un nom à la colonne.")
            elif any(c["name"] == name_clean for c in table["columns"]):
                st.error("Une colonne avec ce nom existe déjà.")
            else:
                new_columns = table["columns"] + [{
                    "name": name_clean,
                    "type": _TYPE_TO_API[tp],
                    "role": role,
                }]
                resp = requests.put(
                    f"{API_BASE}/tables/{table['id']}",
                    json={"columns": new_columns}, timeout=5,
                )
                if resp.ok:
                    st.session_state.pop(f"{key_prefix}_name", None)
                    st.rerun()
                else:
                    st.error(f"Erreur API ({resp.status_code}) : {resp.text}")


def render(table_id: str | None = None) -> None:
    """
    Affiche la page d'édition des règles : tableau éditable, ajout/suppression de colonnes,
    import/export JSON, sauvegarde via PUT /tables/{id}.
    Entrée : table_id — UUID présélectionné (ou None pour le premier de la liste).
    """
    _init_state()
    tables = api_get("/tables") or []
    if not tables:
        st.info("Aucune table disponible.")
        return

    default_idx = 0
    if table_id:
        for i, t in enumerate(tables):
            if t["id"] == table_id:
                default_idx = i
                break

    id_to_table = {t["id"]: t for t in tables}
    selected_id = st.selectbox(
        "Table", options=list(id_to_table.keys()),
        format_func=lambda tid: id_to_table[tid]["name"],
        index=default_idx,
        key="table_selector", label_visibility="collapsed",
    )
    table = id_to_table[selected_id]
    _reset_edit_state(table["id"])

    input_cols  = [c for c in table["columns"] if c["role"] == "input"]
    output_cols = [c for c in table["columns"] if c["role"] == "output"]
    rules = table.get("rules", [])

    # ── Breadcrumb ────────────────────────────────────────────────────────────
    st.markdown(
        f'<p style="font-size:0.9rem; color:#6b7280; margin-bottom:4px;">'
        f'<a href="?page=tables" target="_self" style="color:#4c8c6b; text-decoration:none;">Tables</a>'
        f' &rsaquo; <a href="?page=detail&table_id={table["id"]}" target="_self" style="color:#4c8c6b; text-decoration:none;">'
        f'{_esc(table["name"])}</a> &rsaquo; Règles</p>',
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
        st.session_state["mr_show_import"] = not st.session_state["mr_show_import"]

    if st.session_state["mr_show_import"]:
        uploaded = st.file_uploader(
            "Fichier JSON de règles", type="json",
            key=f"mr_upload_{st.session_state['mr_upload_key']}",
        )
        if uploaded:
            try:
                data = json.loads(uploaded.read())
                new_rules = data.get("rules", data) if isinstance(data, dict) else data
                resp = requests.put(
                    f"{API_BASE}/tables/{table['id']}",
                    json={"rules": rules + new_rules}, timeout=5,
                )
                if resp.ok:
                    st.session_state["mr_show_import"] = False
                    st.session_state["mr_upload_key"] += 1
                    st.success(f"{len(new_rules)} règle(s) importée(s).")
                    st.rerun()
                else:
                    st.error(f"Erreur API ({resp.status_code}) : {resp.text}")
            except Exception as e:
                st.error(f"Fichier invalide : {e}")

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

    if not input_cols and not output_cols:
        st.info("Cette table n'a pas de colonnes.")
        ec1, ec2 = st.columns(2)
        with ec1:
            st.markdown("Ajouter une entrée")
            _add_column_popover(table, "input", "mc_in_empty")
        with ec2:
            st.markdown("Ajouter une sortie")
            _add_column_popover(table, "output", "mc_out_empty")
        return

    n_in, n_out = len(input_cols), len(output_cols)
    IN_BTN  = n_in + 1
    OUT_BTN = n_in + 2 + n_out
    col_widths = [0.5] + [2.5] * n_in + [0.5] + [2.5] * n_out + [0.5] + [0.6]

    st.markdown(_TABLE_CSS + '<div class="rules-wrapper">', unsafe_allow_html=True)

    # ── En-tête noms ─────────────────────────────────────────────────────────
    h_row = st.columns(col_widths)
    h_row[0].markdown(_cell("#", "#1e293b", align="center"), unsafe_allow_html=True)
    for i, c in enumerate(input_cols):
        h_row[i + 1].markdown(
            _cell(f"<span style='font-size:.83rem; font-weight:600; color:#fff;'>{_esc(c['name'])}</span>", "#1b3a2f"),
            unsafe_allow_html=True,
        )
    with h_row[IN_BTN]:
        _add_column_popover(table, "input", "mc_in")
    for i, c in enumerate(output_cols):
        h_row[IN_BTN + 1 + i].markdown(
            _cell(f"<span style='font-size:.83rem; font-weight:600; color:#fff;'>{_esc(c['name'])}</span>", "#15803d"),
            unsafe_allow_html=True,
        )
    with h_row[OUT_BTN]:
        _add_column_popover(table, "output", "mc_out")
    h_row[-1].markdown(_cell("", "#374151"), unsafe_allow_html=True)

    # ── En-tête types ─────────────────────────────────────────────────────────
    t_row = st.columns(col_widths)
    t_row[0].markdown(_cell("", "#1e293b", height="24px"), unsafe_allow_html=True)
    for i, c in enumerate(input_cols):
        t_row[i + 1].markdown(
            _cell(f"<span style='font-size:.74rem; color:#d1d5db;'>{_TYPE_FR.get(c['type'])}</span>", "#1b3a2f", height="24px"),
            unsafe_allow_html=True,
        )
    t_row[IN_BTN].markdown(_cell("", "#ffffff", height="24px"), unsafe_allow_html=True)
    for i, c in enumerate(output_cols):
        t_row[IN_BTN + 1 + i].markdown(
            _cell(f"<span style='font-size:.74rem; color:#d1d5db;'>{_TYPE_FR.get(c['type'])}</span>", "#15803d", height="24px"),
            unsafe_allow_html=True,
        )
    t_row[OUT_BTN].markdown(_cell("", "#ffffff", height="24px"), unsafe_allow_html=True)
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

        d_row[IN_BTN].markdown(
            "<div style='height:43px;border-bottom:1px solid #f0f0f0;'></div>", unsafe_allow_html=True)

        for i, c in enumerate(output_cols):
            with d_row[IN_BTN + 1 + i]:
                current = str(rule.get("output", {}).get(c["name"], ""))
                st.text_input(
                    c["name"], value=current,
                    key=f"out_{idx}_{c['name']}",
                    label_visibility="collapsed",
                )

        d_row[OUT_BTN].markdown(
            "<div style='height:43px;border-bottom:1px solid #f0f0f0;'></div>", unsafe_allow_html=True)

        with d_row[-1]:
            if st.button("✕", key=f"del_{idx - 1}"):
                _save_rules(table["id"], [r for j, r in enumerate(rules) if j != idx - 1])
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Sauvegarde de toutes les règles ───────────────────────────────────────
    if save_clicked:
        updated_rules = []
        empty_output_rows = []
        for idx, rule in enumerate(rules, start=1):
            conditions = {}
            for c in input_cols:
                val = str(st.session_state.get(f"cond_{idx}_{c['name']}", "")).strip()
                if val:
                    conditions[c["name"]] = val
            outputs = {}
            for c in output_cols:
                val = str(st.session_state.get(f"out_{idx}_{c['name']}", "")).strip()
                if val:
                    outputs[c["name"]] = val
                else:
                    empty_output_rows.append(idx)
            updated_rules.append({"conditions": conditions, "output": outputs})
        if empty_output_rows:
            rows_str = ", ".join(str(r) for r in sorted(set(empty_output_rows)))
            st.warning(f"⚠️ Règle(s) {rows_str} : valeur de sortie vide — la simulation ne retournera aucun résultat pour ces règles.")
        _save_rules(table["id"], updated_rules)
        st.toast("Table à jour !", icon="✅")

    # ── Ajouter une règle ─────────────────────────────────────────────────────
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    if st.button("＋  Ajouter une règle", use_container_width=True):
        st.session_state["show_add_rule"] = not st.session_state.get("show_add_rule", False)
        st.rerun()

    if st.session_state.get("show_add_rule"):
        with st.container(border=True):
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

            if st.button("Ajouter la règle", use_container_width=True, type="primary", key="mr_add_submit"):
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

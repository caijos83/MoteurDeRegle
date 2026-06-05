"""
IHM DMN Light — Streamlit
Interface métier pour créer, éditer et simuler des tables de décision.
"""

import streamlit as st
import requests

API_BASE = "http://localhost:8000/api/v1"

# ── Traductions métier ────────────────────────────────────────────────────────
TYPE_OPTIONS   = ["Nombre", "Texte", "Oui / Non"]
TYPE_TO_API    = {"Nombre": "number", "Texte": "text", "Oui / Non": "boolean"}
TYPE_FROM_API  = {"number": "Nombre", "text": "Texte", "boolean": "Oui / Non"}

POLICY_OPTIONS = ["Première règle applicable", "Additionner tous les résultats"]
POLICY_TO_API  = {
    "Première règle applicable":      "FIRST",
    "Additionner tous les résultats": "COLLECT SUM",
}
POLICY_FROM_API = {v: k for k, v in POLICY_TO_API.items()}

OPERATORS_NUMBER  = [">", "<", "≥", "≤", "=", "≠", "entre … et …"]
OPERATORS_TEXT    = ["est égal à", "fait partie de la liste"]
OPERATORS_BOOLEAN = ["est Vrai", "est Faux"]

OP_TO_SYNTAX = {">": ">", "<": "<", "≥": ">=", "≤": "<=", "=": "=", "≠": "!="}


# ── Helpers ───────────────────────────────────────────────────────────────────
def api_get(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        return r.json() if r.ok else None
    except Exception:
        return None


def build_condition(col_type, operator, value, value2=""):
    if col_type == "number":
        if operator == "entre … et …":
            return f"[{value}..{value2}]"
        return f"{OP_TO_SYNTAX[operator]} {value}"
    if col_type == "text":
        if operator == "fait partie de la liste":
            items = [v.strip() for v in value.split(",")]
            return '["' + '","'.join(items) + '"]'
        return value
    if col_type == "boolean":
        return "true" if operator == "est Vrai" else "false"
    return value


def render_condition(raw, col_type):
    """Affiche une condition brute en libellé lisible."""
    if col_type == "boolean":
        return "Vrai" if raw == "true" else "Faux"
    for sym, op in OP_TO_SYNTAX.items():
        raw = raw.replace(op + " ", sym + " ", 1)
    raw = raw.replace("[", "entre ").replace("..", " et ").replace("]", "")
    return raw


def condition_form(col, key_prefix):
    """Affiche le formulaire de saisie d'une condition selon le type de colonne."""
    ct = col["type"]
    if ct == "number":
        op = st.selectbox("Opérateur", OPERATORS_NUMBER, key=f"{key_prefix}_op")
        if op == "entre … et …":
            c1, c2 = st.columns(2)
            v1 = c1.number_input("De", key=f"{key_prefix}_v1", step=1.0)
            v2 = c2.number_input("À",  key=f"{key_prefix}_v2", step=1.0)
            return build_condition(ct, op, v1, v2)
        v = st.number_input("Valeur", key=f"{key_prefix}_v", step=1.0)
        return build_condition(ct, op, v)
    if ct == "text":
        op = st.selectbox("Opérateur", OPERATORS_TEXT, key=f"{key_prefix}_op")
        if op == "fait partie de la liste":
            v = st.text_input("Valeurs séparées par des virgules", key=f"{key_prefix}_v")
        else:
            v = st.text_input("Valeur", key=f"{key_prefix}_v")
        return build_condition(ct, op, v)
    if ct == "boolean":
        op = st.selectbox("Valeur", OPERATORS_BOOLEAN, key=f"{key_prefix}_op")
        return build_condition(ct, op, "")
    return ""


# ── Configuration de la page ──────────────────────────────────────────────────
st.set_page_config(page_title="Moteur de Règles", layout="wide", page_icon="⚖️")

st.sidebar.title("⚖️ Moteur de Règles")
page = st.sidebar.radio(
    "Menu",
    ["Mes tables", "Nouvelle table", "Gérer les règles", "Simuler une décision"],
    label_visibility="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE — Mes tables
# ═══════════════════════════════════════════════════════════════════════════════
if page == "Mes tables":
    st.title("Mes tables de décision")

    tables = api_get("/tables") or []

    if not tables:
        st.info("Aucune table créée pour l'instant. Utilisez « Nouvelle table » pour commencer.")
    else:
        for t in tables:
            nb_rules = len(t.get("rules", []))
            nb_inputs = sum(1 for c in t["columns"] if c["role"] == "input")
            nb_outputs = sum(1 for c in t["columns"] if c["role"] == "output")

            with st.container(border=True):
                col_info, col_actions = st.columns([5, 1])
                with col_info:
                    st.subheader(t["name"])
                    st.caption(
                        f"Politique : **{POLICY_FROM_API.get(t['hit_policy'], t['hit_policy'])}**"
                        f"  |  {nb_inputs} critère(s) d'entrée"
                        f"  |  {nb_outputs} résultat(s)"
                        f"  |  {nb_rules} règle(s)"
                    )
                with col_actions:
                    if st.button("🗑️ Supprimer", key=f"del_{t['id']}"):
                        requests.delete(f"{API_BASE}/tables/{t['id']}")
                        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE — Nouvelle table
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Nouvelle table":
    st.title("Créer une table de décision")

    with st.form("create_table", border=True):
        name = st.text_input("Nom de la table", placeholder="ex. Éligibilité crédit")

        policy_label = st.radio(
            "Politique de décision",
            POLICY_OPTIONS,
            captions=[
                "Dès qu'une règle correspond, sa réponse est retournée.",
                "Toutes les règles correspondantes sont sommées.",
            ],
        )

        st.divider()
        st.subheader("Critères d'entrée")
        st.caption("Ce sont les données fournies lors de la simulation.")
        n_in = st.number_input("Nombre de critères", min_value=1, max_value=10, value=2, step=1)
        inputs = []
        for i in range(int(n_in)):
            c1, c2 = st.columns([2, 1])
            col_name = c1.text_input(f"Critère {i+1}", key=f"in_name_{i}", placeholder="ex. age")
            col_type = c2.selectbox("Type", TYPE_OPTIONS, key=f"in_type_{i}")
            inputs.append({"name": col_name, "type": TYPE_TO_API[col_type], "role": "input"})

        st.divider()
        st.subheader("Résultats")
        st.caption("Ce que la table retourne comme décision.")
        n_out = st.number_input("Nombre de résultats", min_value=1, max_value=5, value=1, step=1)
        outputs = []
        for i in range(int(n_out)):
            c1, c2 = st.columns([2, 1])
            col_name = c1.text_input(f"Résultat {i+1}", key=f"out_name_{i}", placeholder="ex. décision")
            col_type = c2.selectbox("Type", TYPE_OPTIONS, key=f"out_type_{i}")
            outputs.append({"name": col_name, "type": TYPE_TO_API[col_type], "role": "output"})

        submitted = st.form_submit_button("Créer la table", use_container_width=True, type="primary")
        if submitted:
            if not name.strip():
                st.error("Veuillez saisir un nom pour la table.")
            elif any(not c["name"].strip() for c in inputs + outputs):
                st.error("Veuillez nommer tous les critères et résultats.")
            else:
                resp = requests.post(f"{API_BASE}/tables", json={
                    "name": name.strip(),
                    "hit_policy": POLICY_TO_API[policy_label],
                    "columns": inputs + outputs,
                })
                if resp.status_code == 201:
                    st.success(f"Table **{name}** créée avec succès.")
                else:
                    st.error("Erreur lors de la création.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE — Gérer les règles
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Gérer les règles":
    st.title("Gérer les règles")

    tables = api_get("/tables") or []
    if not tables:
        st.info("Aucune table disponible.")
        st.stop()

    table_map = {t["name"]: t for t in tables}
    selected_name = st.selectbox("Choisir une table", list(table_map.keys()))
    table = table_map[selected_name]

    input_cols  = [c for c in table["columns"] if c["role"] == "input"]
    output_cols = [c for c in table["columns"] if c["role"] == "output"]
    rules = table.get("rules", [])

    # ── Tableau des règles ────────────────────────────────────────────────────
    st.subheader(f"Règles de « {table['name']} »")
    st.caption(f"Politique : **{POLICY_FROM_API.get(table['hit_policy'], table['hit_policy'])}**")

    if not rules:
        st.info("Aucune règle. Ajoutez-en une ci-dessous.")
    else:
        header_cols = st.columns(len(input_cols) + len(output_cols) + 1)
        for i, col in enumerate(input_cols):
            header_cols[i].markdown(f"**{col['name']}** *(entrée)*")
        for i, col in enumerate(output_cols):
            header_cols[len(input_cols) + i].markdown(f"**{col['name']}** *(résultat)*")
        header_cols[-1].markdown("**Action**")

        st.divider()

        for r_idx, rule in enumerate(rules):
            row = st.columns(len(input_cols) + len(output_cols) + 1)
            for i, col in enumerate(input_cols):
                raw = rule["conditions"].get(col["name"], "—")
                row[i].write(render_condition(raw, col["type"]) if raw != "—" else "—")
            for i, col in enumerate(output_cols):
                row[len(input_cols) + i].write(rule["output"].get(col["name"], "—"))
            if row[-1].button("🗑️", key=f"del_rule_{r_idx}"):
                new_rules = [r for idx, r in enumerate(rules) if idx != r_idx]
                requests.put(f"{API_BASE}/tables/{table['id']}", json={"rules": new_rules})
                st.rerun()

    # ── Formulaire d'ajout de règle ───────────────────────────────────────────
    st.divider()
    st.subheader("Ajouter une règle")

    with st.form("add_rule", border=True):
        conditions = {}
        outputs_vals = {}

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
                outputs_vals[col["name"]] = str(val)
            elif col["type"] == "boolean":
                val = st.selectbox(col["name"], ["Vrai", "Faux"], key=f"out_{col['name']}")
                outputs_vals[col["name"]] = "true" if val == "Vrai" else "false"
            else:
                val = st.text_input(col["name"], key=f"out_{col['name']}")
                outputs_vals[col["name"]] = val

        if st.form_submit_button("Ajouter la règle", use_container_width=True, type="primary"):
            if not all(outputs_vals.values()):
                st.error("Veuillez renseigner tous les résultats.")
            else:
                new_rule = {"conditions": conditions, "output": outputs_vals}
                resp = requests.put(f"{API_BASE}/tables/{table['id']}", json={
                    "rules": rules + [new_rule]
                })
                if resp.ok:
                    st.success("Règle ajoutée.")
                    st.rerun()
                else:
                    st.error("Erreur lors de l'ajout.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE — Simuler une décision
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Simuler une décision":
    st.title("Simuler une décision")

    tables = api_get("/tables") or []
    if not tables:
        st.info("Aucune table disponible.")
        st.stop()

    table_map = {t["name"]: t for t in tables}
    selected_name = st.selectbox("Table à utiliser", list(table_map.keys()))
    table = table_map[selected_name]

    input_cols = [c for c in table["columns"] if c["role"] == "input"]

    with st.form("simulate", border=True):
        st.subheader("Valeurs à tester")
        inputs = {}
        for col in input_cols:
            label = col["name"]
            if col["type"] == "number":
                v = st.number_input(label, key=f"sim_{col['name']}", step=1.0)
                inputs[col["name"]] = v
            elif col["type"] == "boolean":
                v = st.selectbox(label, ["Vrai", "Faux"], key=f"sim_{col['name']}")
                inputs[col["name"]] = "true" if v == "Vrai" else "false"
            else:
                v = st.text_input(label, key=f"sim_{col['name']}")
                inputs[col["name"]] = v

        run = st.form_submit_button("Obtenir la décision", use_container_width=True, type="primary")

    if run:
        resp = requests.post(f"{API_BASE}/tables/{table['id']}/evaluate",
                             json={"inputs": inputs})
        if resp.ok:
            data = resp.json()
            result = data.get("result")
            nb_matched = data.get("matched_rules")

            st.divider()
            st.subheader("Résultat")

            if result is None:
                st.warning("Aucune règle ne correspond aux valeurs saisies.")
            elif isinstance(result, dict):
                for k, v in result.items():
                    st.metric(label=k, value=v)
            else:
                output_cols = [c for c in table["columns"] if c["role"] == "output"]
                label = output_cols[0]["name"] if output_cols else "Résultat"
                st.metric(label=label, value=result)

            if nb_matched is not None:
                st.caption(f"{nb_matched} règle(s) appliquée(s).")
        else:
            detail = resp.json().get("detail", "Erreur inconnue.")
            st.error(f"Impossible d'évaluer : {detail}")

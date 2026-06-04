"""
IHM DMN Light — Streamlit
Permet de créer, éditer et exécuter des tables de décision.
"""

import streamlit as st
import requests
import json

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(page_title="DMN Light", layout="wide")
st.title("Moteur de Règles DMN Light")

# ------------------------------------------------------------------
# Navigation
# ------------------------------------------------------------------
page = st.sidebar.radio(
    "Navigation",
    ["Lister les tables", "Créer une table", "Éditer une table", "Exécuter / Tester"]
)

# ------------------------------------------------------------------
# Page : liste des tables
# ------------------------------------------------------------------
if page == "Lister les tables":
    st.header("Tables de décision")
    resp = requests.get(f"{API_BASE}/tables")
    if resp.status_code == 200:
        tables = resp.json()
        if not tables:
            st.info("Aucune table créée.")
        for t in tables:
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"**{t['name']}** — {t['hit_policy']}")
            col2.write(f"{len(t.get('rules', []))} règle(s)")
            if col3.button("Supprimer", key=f"del_{t['id']}"):
                requests.delete(f"{API_BASE}/tables/{t['id']}")
                st.rerun()
    else:
        st.error("Impossible de joindre l'API.")

# ------------------------------------------------------------------
# Page : créer une table
# ------------------------------------------------------------------
elif page == "Créer une table":
    st.header("Créer une table de décision")
    with st.form("create_table"):
        name = st.text_input("Nom de la table")
        hit_policy = st.selectbox("Hit Policy", ["FIRST", "COLLECT SUM"])
        st.subheader("Colonnes")
        n_cols = st.number_input("Nombre de colonnes", min_value=1, max_value=10, value=2)
        columns = []
        for i in range(int(n_cols)):
            c1, c2, c3 = st.columns(3)
            col_name = c1.text_input(f"Nom colonne {i+1}", key=f"cn_{i}")
            col_type = c2.selectbox("Type", ["number", "text", "boolean"], key=f"ct_{i}")
            col_role = c3.selectbox("Rôle", ["input", "output"], key=f"cr_{i}")
            columns.append({"name": col_name, "type": col_type, "role": col_role})
        submitted = st.form_submit_button("Créer")
        if submitted and name:
            resp = requests.post(f"{API_BASE}/tables", json={
                "name": name,
                "hit_policy": hit_policy,
                "columns": columns,
            })
            if resp.status_code == 201:
                st.success(f"Table '{name}' créée.")
            else:
                st.error(f"Erreur : {resp.json()}")

# ------------------------------------------------------------------
# Page : éditer une table (ajout de règles)
# ------------------------------------------------------------------
elif page == "Éditer une table":
    st.header("Éditer une table")
    resp = requests.get(f"{API_BASE}/tables")
    tables = resp.json() if resp.status_code == 200 else []
    if not tables:
        st.info("Aucune table disponible.")
    else:
        table_names = {t["name"]: t["id"] for t in tables}
        selected = st.selectbox("Choisir une table", list(table_names.keys()))
        table_id = table_names[selected]
        table = requests.get(f"{API_BASE}/tables/{table_id}").json()
        st.json(table)

        st.subheader("Ajouter une règle")
        input_cols = [c for c in table["columns"] if c["role"] == "input"]
        output_cols = [c for c in table["columns"] if c["role"] == "output"]

        with st.form("add_rule"):
            conditions = {}
            for col in input_cols:
                expr = st.text_input(f"Condition sur '{col['name']}' ({col['type']})",
                                     help="Ex: >= 18, [18..65], [\"A\",\"B\"]")
                if expr:
                    conditions[col["name"]] = expr
            output = {}
            for col in output_cols:
                val = st.text_input(f"Output '{col['name']}'")
                if val:
                    output[col["name"]] = val
            if st.form_submit_button("Ajouter la règle"):
                resp = requests.put(f"{API_BASE}/tables/{table_id}", json={
                    "rules": table.get("rules", []) + [{"conditions": conditions, "output": output}]
                })
                if resp.status_code == 200:
                    st.success("Règle ajoutée.")
                    st.rerun()

# ------------------------------------------------------------------
# Page : exécuter / tester
# ------------------------------------------------------------------
elif page == "Exécuter / Tester":
    st.header("Exécuter une table")
    resp = requests.get(f"{API_BASE}/tables")
    tables = resp.json() if resp.status_code == 200 else []
    if not tables:
        st.info("Aucune table disponible.")
    else:
        table_names = {t["name"]: t["id"] for t in tables}
        selected = st.selectbox("Choisir une table", list(table_names.keys()))
        table_id = table_names[selected]
        table = requests.get(f"{API_BASE}/tables/{table_id}").json()
        input_cols = [c for c in table["columns"] if c["role"] == "input"]

        with st.form("evaluate"):
            inputs = {}
            for col in input_cols:
                val = st.text_input(f"Valeur de '{col['name']}' ({col['type']})")
                inputs[col["name"]] = val
            if st.form_submit_button("Évaluer"):
                resp = requests.post(f"{API_BASE}/tables/{table_id}/evaluate",
                                     json={"inputs": inputs})
                if resp.status_code == 200:
                    result = resp.json()
                    st.success("Résultat :")
                    st.json(result)
                else:
                    st.error(f"Erreur : {resp.json()}")

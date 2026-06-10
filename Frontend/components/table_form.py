import streamlit as st
import uuid
from utils.api_client import create_table

def create_table_form(name, hit_policy, description):
    if not name.strip():
        st.warning("⚠️ Le nom de la table est obligatoire")
        return

    st.subheader("Colonnes d'entrée (critères)")

    if 'input_columns' not in st.session_state:
        st.session_state.input_columns = [
            {"name": "revenu", "type": "number"},
            {"name": "historique_credit", "type": "text"},
            {"name": "est_proprietaire", "type": "boolean"}
        ]

    for i, col in enumerate(st.session_state.input_columns):
        cols = st.columns([3, 2, 1])
        with cols[0]:
            col["name"] = st.text_input("Nom", value=col["name"], key=f"name_{i}")
        with cols[1]:
            col["type"] = st.selectbox("Type", ["number", "text", "boolean"], 
                                     key=f"type_{i}")
        with cols[2]:
            if st.button("🗑️", key=f"delete_{i}"):
                st.session_state.input_columns.pop(i)
                st.rerun()

    if st.button("➕ Ajouter colonne", use_container_width=True):
        st.session_state.input_columns.append({"name": "nouveau_critere", "type": "number"})
        st.rerun()

    st.divider()
    st.subheader("Colonne de sortie")
    output_name = st.text_input("Nom de la sortie", 
                               value="score" if hit_policy == "COLLECT SUM" else "decision")

    if st.button("💾 Créer et Enregistrer la table", type="primary", use_container_width=True):
        columns = st.session_state.input_columns.copy()
        columns.append({"name": output_name, "type": "number" if hit_policy == "COLLECT SUM" else "text", "role": "output"})

        table_data = {
            "id": str(uuid.uuid4()),
            "name": name,
            "hit_policy": hit_policy,
            "description": description,
            "columns": columns
        }

        if create_table(table_data):
            st.success("✅ Table créée avec succès !")
            st.balloons()
        else:
            st.error("❌ Erreur lors de la création")
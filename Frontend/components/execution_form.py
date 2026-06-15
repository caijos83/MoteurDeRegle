import streamlit as st
from utils.api_client import evaluate_table

def execution_form(table):
    st.subheader("Valeurs d'entrée")
    
    input_cols = [c for c in table.get("columns", []) if c.get("role") != "output"]
    inputs = {}

    for col in input_cols:
        name = col["name"]
        ctype = col.get("type")
        if ctype == "number":
            inputs[name] = st.number_input(name, value=32)
        elif ctype == "boolean":
            inputs[name] = st.checkbox(name, value=True)
        else:
            inputs[name] = st.text_input(name, value="CDI")

    if st.button("▶️ Évaluer", type="primary", use_container_width=True):
        with st.spinner("Évaluation en cours..."):
            return evaluate_table(table["id"], inputs)
    return None
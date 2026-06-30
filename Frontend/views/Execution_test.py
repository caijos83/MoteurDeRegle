import streamlit as st
from components.execution_form import execution_form
from components.result_display import display_results
from utils.api_client import list_tables

def show():
    st.title("Tester la table")
    
    tables = list_tables()
    if not tables:
        st.warning("Aucune table disponible.")
        return

    selected_name = st.selectbox("Table", [t["name"] for t in tables])
    selected_table = next(t for t in tables if t["name"] == selected_name)

    result = execution_form(selected_table)
    if result:
        display_results(result, selected_table)
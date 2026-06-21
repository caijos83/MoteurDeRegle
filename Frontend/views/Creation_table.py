import streamlit as st
from components.table_form import create_table_form

def show():
    st.title("➕ Créer une table de décision")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Informations générales")
        name = st.text_input("Nom de la table *", placeholder="Score risque client")
        description = st.text_area("Description", 
                                  "Calcule un score de risque basé sur le profil client", 
                                  height=100)
        
        st.subheader("Hit Policy *")
        hit_policy = st.radio("", ["First", "Collect Sum"], 
                            horizontal=True, 
                            label_visibility="collapsed")
        
    with col2:
        st.subheader("Colonnes d'entrée (critères)")
        create_table_form(name, hit_policy, description)
import streamlit as st

def display_results(result, table):
    if not result:
        return

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.success("**Résultat — Collect Sum**")
        res = result.get("result", 0)
        st.markdown(f"<h1 style='color:#10b981; text-align:center;'>+{res}</h1>", unsafe_allow_html=True)
        st.caption("Score total")

    with col2:
        st.subheader("Détail des règles évaluées")
        # Simulation ou données réelles
        st.info("Règle 1 — match - score +30")
        st.info("Règle 3 — match - score -5")
        st.caption(f"Temps d'évaluation : {result.get('time', '2')} ms")
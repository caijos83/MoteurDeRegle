import streamlit as st
import requests
from utils.api import (
    API_BASE, TYPE_OPTIONS, TYPE_TO_API,
    POLICY_TO_API,
)

_POLICY_OPTIONS = list(POLICY_TO_API.keys())


def render() -> None:
    # ── Breadcrumb ────────────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:0.9rem; color:#6b7280; margin-bottom:4px;">'
        '<a href="?page=tables" style="color:#4f46e5; text-decoration:none;">Tables</a>'
        " &rsaquo; Nouvelle table</p>",
        unsafe_allow_html=True,
    )
    st.markdown("## Nouvelle table de décision")
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    with st.form("create_table", border=True):
        name = st.text_input("Nom de la table", placeholder="ex. Éligibilité crédit")

        policy_label = st.radio(
            "Politique de décision",
            _POLICY_OPTIONS,
            captions=[
                "Dès qu'une règle correspond, sa réponse est retournée.",
                "Toutes les règles correspondantes sont sommées.",
            ],
        )

        st.divider()
        st.subheader("Critères d'entrée")
        st.caption("Données fournies lors de la simulation.")
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
            resp = requests.post(
                f"{API_BASE}/tables",
                json={"name": name.strip(), "hit_policy": POLICY_TO_API[policy_label], "columns": inputs + outputs},
                timeout=5,
            )
            if resp.status_code == 201:
                created = resp.json()
                st.success(f"Table **{name}** créée avec succès.")
                if st.button("Voir la table →"):
                    st.query_params["page"] = "detail"
                    st.query_params["table_id"] = created.get("id", "")
                    st.rerun()
            else:
                st.error("Erreur lors de la création.")

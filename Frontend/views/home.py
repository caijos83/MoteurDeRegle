import streamlit as st
from utils.api import api_get

_HOME_CSS = """
<style>
.home-hero {
    text-align: center !important;
    padding: 56px 0 28px !important;
}
.home-title {
    font-size: 3.4rem !important;
    font-weight: 800 !important;
    color: #0f172a !important;
    letter-spacing: -0.02em !important;
    margin: 0 !important;
    line-height: 1.15 !important;
}
.home-title span { color: #2563eb !important; }
.home-tagline {
    font-size: 1.1rem !important;
    color: #64748b !important;
    margin: 14px auto 0 !important;
    max-width: 580px !important;
    line-height: 1.5 !important;
}
.home-stats {
    display: flex;
    justify-content: center;
    gap: 16px;
    margin: 36px 0 48px;
    flex-wrap: wrap;
}
.home-stat {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
    padding: 18px 30px;
    min-width: 150px;
    text-align: center;
}
.home-stat .num { font-size: 1.9rem !important; font-weight: 800 !important; color: #2563eb !important; margin: 0 !important; }
.home-stat .lbl {
    font-size: 0.76rem !important; color: #64748b !important; text-transform: uppercase;
    letter-spacing: 0.05em; margin-top: 4px !important;
}
.home-steps {
    display: flex;
    gap: 20px;
    max-width: 900px;
    margin: 0 auto 40px;
    flex-wrap: wrap;
    justify-content: center;
}
.home-step {
    flex: 1;
    min-width: 230px;
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 14px;
    padding: 22px 20px;
}
.home-step .step-num {
    display: inline-flex;
    width: 28px; height: 28px;
    align-items: center; justify-content: center;
    background: #2563eb; color: #fff;
    border-radius: 50%;
    font-weight: 700; font-size: 0.85rem;
    margin-bottom: 10px;
}
.home-step h4 { margin: 0 0 6px !important; font-size: 1rem !important; color: #0f172a !important; }
.home-step p { margin: 0 !important; font-size: 0.86rem !important; color: #64748b !important; line-height: 1.45 !important; }

/* Bouton principal de la page Home — bleu, cohérent avec le reste de l'app */
div.stButton > button[kind="primary"] {
    background: #2563eb !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600 !important;
}
div.stButton > button[kind="primary"]:hover {
    background: #1d4ed8 !important;
}
</style>
"""


def render() -> None:
    tables = api_get("/tables") or []
    nb_tables = len(tables)
    nb_first  = sum(1 for t in tables if t.get("hit_policy") == "FIRST")
    nb_sum    = nb_tables - nb_first
    nb_rules  = sum(len(t.get("rules", [])) for t in tables)

    st.markdown(_HOME_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="home-hero">'
        '<p class="home-title">DMN<span>Light</span></p>'
        '<p class="home-tagline">Moteur de règles métier léger pour vos tables de décision. '
        'Définissez vos critères, ajoutez vos règles, obtenez une décision ou un score — '
        'en local, sans dépendance cloud.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    _, c2, _ = st.columns([1, 1, 1])
    with c2:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("📁  Voir mes tables", use_container_width=True, type="primary"):
                st.query_params["page"] = "tables"
                st.rerun()
        with b2:
            if st.button("＋  Créer une table", use_container_width=True):
                st.query_params["page"] = "new_table"
                st.rerun()

    st.markdown(
        f'<div class="home-stats">'
        f'<div class="home-stat"><div class="num">{nb_tables}</div><div class="lbl">Tables actives</div></div>'
        f'<div class="home-stat"><div class="num">{nb_rules}</div><div class="lbl">Règles définies</div></div>'
        f'<div class="home-stat"><div class="num">{nb_first}</div><div class="lbl">Hit policy First</div></div>'
        f'<div class="home-stat"><div class="num">{nb_sum}</div><div class="lbl">Hit policy Collect Sum</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="home-steps">'
        '<div class="home-step"><span class="step-num">1</span>'
        '<h4>Créer une table</h4>'
        '<p>Définissez vos critères (entrées) et vos résultats (sorties) — '
        'nombre, texte ou booléen.</p></div>'
        '<div class="home-step"><span class="step-num">2</span>'
        '<h4>Ajouter des règles</h4>'
        '<p>Combinez vos critères avec des opérateurs (&gt;, &lt;, =, intervalles, '
        'listes) pour chaque règle.</p></div>'
        '<div class="home-step"><span class="step-num">3</span>'
        '<h4>Évaluer</h4>'
        '<p>Testez vos règles depuis l\'IHM, ou interrogez-les via l\'API REST, '
        'GraphQL ou MCP.</p></div>'
        '</div>',
        unsafe_allow_html=True,
    )

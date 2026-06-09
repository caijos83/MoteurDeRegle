import json
import streamlit as st
import requests
from utils.api import API_BASE, fmt_condition, fmt_output_html, condition_form

_TYPE_LABELS = ["numérique", "texte", "booléen"]
_TYPE_TO_API = {"numérique": "number", "texte": "text", "booléen": "boolean"}
_TYPE_FR     = {"number": "numérique", "text": "texte", "boolean": "booléen"}

# ── CSS global pour cette page ─────────────────────────────────────────────────
_PAGE_CSS = """
<style>
/* Cartes Hit Policy */
div[data-testid="stRadio"] [data-baseweb="radio-group"] {
    display: flex !important; flex-direction: row !important; gap: 12px !important;
}
div[data-testid="stRadio"] [data-baseweb="radio"] {
    flex: 1 !important; border: 2px solid #e5e7eb !important;
    border-radius: 8px !important; padding: 14px 16px !important;
    cursor: pointer !important; background: #fff !important;
}
div[data-testid="stRadio"] [data-baseweb="radio"]:has(input:checked) {
    border-color: #4f46e5 !important; background: #eef2ff !important;
}
div[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child { display: none !important; }
div[data-testid="stRadio"] [data-baseweb="radio"] p { font-weight: 600 !important; color: #111827 !important; }
div[data-testid="stRadio"] [data-baseweb="radio"] div[data-testid="stCaptionContainer"] p {
    font-size: 0.8rem !important; color: #6b7280 !important; font-weight: normal !important;
}
/* Tableau des règles : supprime le gap entre colonnes */
[data-testid="stHorizontalBlock"] { gap: 0 !important; }
/* Bouton 🗑 dans le tableau */
div.stButton > button[title="del"] {
    border: none !important; border-bottom: 1px solid #f0f0f0 !important;
    border-radius: 0 !important; background: #fafafa !important; color: #d1d5db !important;
    min-height: 43px !important; height: 43px !important; width: 100% !important;
    font-size: 1rem !important; padding: 0 !important;
}
div.stButton > button[title="del"]:hover {
    background: #fee2e2 !important; color: #dc2626 !important;
}
</style>
"""


def _init() -> None:
    for k, v in [("nt_columns", []), ("nt_rules", []), ("nt_show_add", False)]:
        if k not in st.session_state:
            st.session_state[k] = v


def _badge_role(role: str) -> str:
    if role == "input":
        return '<span style="background:#dbeafe;color:#1d4ed8;border-radius:4px;padding:2px 7px;font-size:.75em;font-weight:700;">IN</span>'
    return '<span style="background:#dcfce7;color:#166534;border-radius:4px;padding:2px 7px;font-size:.75em;font-weight:700;">OUT</span>'


def _cell(content: str, bg: str, h: str = "43px", align: str = "left", bb: bool = True) -> str:
    b = "border-bottom:1px solid #f0f0f0;" if bb else ""
    return (f'<div style="background:{bg};height:{h};padding:0 12px;'
            f'display:flex;align-items:center;text-align:{align};{b}box-sizing:border-box;">'
            f'{content}</div>')


def render() -> None:
    _init()
    st.markdown(_PAGE_CSS, unsafe_allow_html=True)

    # ── Breadcrumb ─────────────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:.9rem;color:#6b7280;margin-bottom:4px;">'
        '<a href="?page=tables" style="color:#4f46e5;text-decoration:none;">Tables</a>'
        ' &rsaquo; Nouvelle table</p>', unsafe_allow_html=True)

    # ── Titre + boutons ────────────────────────────────────────────────────────
    ct, cb = st.columns([5, 4])
    with ct:
        st.markdown("## Créer une table de décision")
    with cb:
        st.markdown("<div style='padding-top:18px'></div>", unsafe_allow_html=True)
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("Annuler", use_container_width=True):
                for k in ("nt_columns", "nt_rules", "nt_show_add"):
                    st.session_state.pop(k, None)
                st.query_params["page"] = "tables"
                st.rerun()
        with b2:
            st.download_button(
                "↓ Export",
                data=json.dumps({
                    "name": st.session_state.get("nt_name", ""),
                    "hit_policy": "FIRST" if st.session_state.get("nt_policy", "First") == "First" else "COLLECT SUM",
                    "columns": st.session_state["nt_columns"],
                    "rules":   st.session_state["nt_rules"],
                }, indent=2, ensure_ascii=False),
                file_name="table.json", mime="application/json",
                use_container_width=True,
            )
        with b3:
            do_import = st.button("↑ Import", use_container_width=True)
        with b4:
            save = st.button("✓ Enregistrer", use_container_width=True, type="primary")

    if do_import:
        up = st.file_uploader("Fichier JSON", type="json", key="nt_upload")
        if up:
            try:
                d = json.loads(up.read())
                if "columns" in d:
                    st.session_state["nt_columns"] = d["columns"]
                if "rules" in d:
                    st.session_state["nt_rules"].extend(d["rules"])
                st.rerun()
            except Exception as e:
                st.error(f"Fichier invalide : {e}")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1+2 : Informations générales  |  Colonnes d'entrée
    # ══════════════════════════════════════════════════════════════════════════
    left, gap_col, right = st.columns([5, 0.3, 5])

    with left:
        with st.container(border=True):
            st.markdown("**Informations générales**")
            st.text_input("Nom de la table *", placeholder="ex. Score risque client", key="nt_name")
            st.text_area("Description",
                         placeholder="ex. Calcul du score de risque basé sur le profil client",
                         height=80, key="nt_desc")
            st.markdown("**Hit Policy \\***")
            st.radio("Hit Policy", ["First", "Collect Sum"],
                     captions=["Retourne la 1re règle valide", "Somme de toutes les règles"],
                     label_visibility="collapsed", key="nt_policy")

    with right:
        with st.container(border=True):
            st.markdown("**Colonnes d'entrée (critères)**")

            for i, col in enumerate(st.session_state["nt_columns"]):
                ft = next(k for k, v in _TYPE_TO_API.items() if v == col["type"])
                c1, c2, c3, c4 = st.columns([1.2, 3.5, 2, 0.8])
                c1.markdown(_badge_role(col["role"]), unsafe_allow_html=True)
                c2.markdown(f'<div style="padding-top:4px;font-size:.92rem;">{col["name"]}</div>',
                            unsafe_allow_html=True)
                c3.markdown(f'<div style="padding-top:4px;color:#6b7280;font-size:.88rem;">{ft}</div>',
                            unsafe_allow_html=True)
                if c4.button("🗑", key=f"rc_{i}"):
                    st.session_state["nt_columns"].pop(i)
                    st.rerun()

            st.markdown("<div style='border-top:1px solid #f3f4f6;margin:8px 0 6px'></div>",
                        unsafe_allow_html=True)
            a1, a2, a3, a4 = st.columns([3, 2.2, 1.4, 0.8])
            nn = a1.text_input("N", key="nc_n", label_visibility="collapsed",
                               placeholder="Nom de la colonne")
            nt = a2.selectbox("T", _TYPE_LABELS, key="nc_t", label_visibility="collapsed")
            nr = a3.selectbox("R", ["IN", "OUT"], key="nc_r", label_visibility="collapsed")
            if a4.button("＋", key="nc_add"):
                if nn.strip():
                    st.session_state["nt_columns"].append({
                        "name": nn.strip(),
                        "type": _TYPE_TO_API[nt],
                        "role": "input" if nr == "IN" else "output",
                    })
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 : Règles
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    in_cols  = [c for c in st.session_state["nt_columns"] if c["role"] == "input"]
    out_cols = [c for c in st.session_state["nt_columns"] if c["role"] == "output"]
    rules    = st.session_state["nt_rules"]

    if not in_cols and not out_cols:
        st.info("Ajoutez des colonnes ci-dessus pour définir les règles.")
    else:
        all_c = in_cols + out_cols
        n = len(all_c)
        W = [0.5] + [2.5] * n + [0.6]   # # | données... | 🗑

        # En-tête — noms
        h = st.columns(W)
        h[0].markdown(_cell("#", "#1e293b", h="38px", align="center", bb=False), unsafe_allow_html=True)
        for i, c in enumerate(in_cols):
            h[i+1].markdown(
                _cell(f"<span style='font-size:.83rem;font-weight:600;color:#fff;'>{c['name']}</span>",
                      "#4c3888", h="38px", bb=False), unsafe_allow_html=True)
        for i, c in enumerate(out_cols):
            h[len(in_cols)+1+i].markdown(
                _cell(f"<span style='font-size:.83rem;font-weight:600;color:#fff;'>{c['name']}</span>",
                      "#15803d", h="38px", bb=False), unsafe_allow_html=True)
        h[-1].markdown(_cell("", "#374151", h="38px", bb=False), unsafe_allow_html=True)

        # En-tête — types
        t = st.columns(W)
        t[0].markdown(_cell("", "#1e293b", h="26px", bb=False), unsafe_allow_html=True)
        for i, c in enumerate(in_cols):
            t[i+1].markdown(
                _cell(f"<span style='font-size:.74rem;color:#a78bfa;'>{_TYPE_FR.get(c['type'])}</span>",
                      "#3d2a7a", h="26px", bb=False), unsafe_allow_html=True)
        for i, c in enumerate(out_cols):
            t[len(in_cols)+1+i].markdown(
                _cell(f"<span style='font-size:.74rem;color:#6ee7b7;'>{_TYPE_FR.get(c['type'])}</span>",
                      "#0f5132", h="26px", bb=False), unsafe_allow_html=True)
        t[-1].markdown(_cell("", "#374151", h="26px", bb=False), unsafe_allow_html=True)

        # Lignes de données
        del_idx = None
        for idx, rule in enumerate(rules, start=1):
            bg = "#fff" if idx % 2 else "#fafafa"
            d = st.columns(W)
            d[0].markdown(
                _cell(f"<span style='color:#9ca3af;font-size:.88rem;'>{idx}</span>",
                      bg, align="center"), unsafe_allow_html=True)
            for i, c in enumerate(in_cols):
                raw = rule.get("conditions", {}).get(c["name"], "—")
                d[i+1].markdown(
                    _cell(f"<span style='font-size:.9rem;'>{fmt_condition(raw)}</span>", bg),
                    unsafe_allow_html=True)
            for i, c in enumerate(out_cols):
                val = rule.get("output", {}).get(c["name"], "—")
                d[len(in_cols)+1+i].markdown(_cell(fmt_output_html(val), bg), unsafe_allow_html=True)
            with d[-1]:
                if st.button("🗑", key=f"rd_{idx-1}"):
                    del_idx = idx - 1

        if del_idx is not None:
            st.session_state["nt_rules"].pop(del_idx)
            st.rerun()

        # ── Bouton Ajouter une règle ──────────────────────────────────────────
        if st.button("＋  Ajouter une règle", use_container_width=True):
            st.session_state["nt_show_add"] = not st.session_state["nt_show_add"]
            st.rerun()

        if st.session_state["nt_show_add"]:
            with st.form("nt_add_rule", border=True):
                conditions: dict = {}
                outputs_v: dict = {}

                if in_cols:
                    st.markdown("**Conditions** *(vide = toujours vrai)*")
                    fc_list = st.columns(len(in_cols))
                    for fc, col in zip(fc_list, in_cols):
                        with fc:
                            st.markdown(f"*{col['name']}*")
                            conditions[col["name"]] = condition_form(col, f"ntar_{col['name']}")

                if out_cols:
                    st.divider()
                    st.markdown("**Résultats**")
                    oc_list = st.columns(len(out_cols))
                    for fc, col in zip(oc_list, out_cols):
                        with fc:
                            if col["type"] == "number":
                                v = st.number_input(col["name"], key=f"nto_{col['name']}", step=1.0)
                                outputs_v[col["name"]] = str(int(v) if v == int(v) else v)
                            elif col["type"] == "boolean":
                                v = st.selectbox(col["name"], ["true", "false"], key=f"nto_{col['name']}")
                                outputs_v[col["name"]] = v
                            else:
                                v = st.text_input(col["name"], key=f"nto_{col['name']}")
                                outputs_v[col["name"]] = v

                if st.form_submit_button("Ajouter", use_container_width=True, type="primary"):
                    clean = {k: v for k, v in conditions.items() if v and str(v).strip()}
                    if not all(str(v).strip() for v in outputs_v.values()):
                        st.error("Renseignez tous les résultats.")
                    else:
                        st.session_state["nt_rules"].append({"conditions": clean, "output": outputs_v})
                        st.session_state["nt_show_add"] = False
                        st.rerun()

        # Note opérateurs
        st.markdown(
            '<p style="font-size:.78rem;color:#9ca3af;margin-top:10px;">'
            "Opérateurs supportés : <code>&gt;</code> <code>&lt;</code> <code>=</code>"
            " <code>!=</code> <code>[a..b]</code> <code>liste</code>"
            " · Utilisez <code>—</code> pour ignorer un critère</p>",
            unsafe_allow_html=True)

    # ── Enregistrer ────────────────────────────────────────────────────────────
    if save:
        name_v   = st.session_state.get("nt_name", "").strip()
        cols     = st.session_state["nt_columns"]
        nt_rules = st.session_state["nt_rules"]
        pol_api  = "FIRST" if st.session_state.get("nt_policy", "First") == "First" else "COLLECT SUM"

        if not name_v:
            st.error("Le nom de la table est obligatoire.")
        elif not cols:
            st.error("Ajoutez au moins une colonne.")
        elif not any(c["role"] == "input"  for c in cols):
            st.error("Ajoutez au moins une colonne d'entrée (IN).")
        elif not any(c["role"] == "output" for c in cols):
            st.error("Ajoutez au moins une colonne de sortie (OUT).")
        else:
            r = requests.post(f"{API_BASE}/tables",
                              json={"name": name_v, "hit_policy": pol_api, "columns": cols},
                              timeout=5)
            if r.status_code == 201:
                tid = r.json().get("id", "")
                if nt_rules and tid:
                    requests.put(f"{API_BASE}/tables/{tid}",
                                 json={"rules": nt_rules}, timeout=5)
                for k in ("nt_columns", "nt_rules", "nt_show_add"):
                    st.session_state.pop(k, None)
                st.query_params["page"] = "detail"
                st.query_params["table_id"] = tid
                st.rerun()
            else:
                st.error(f"Erreur : {r.text}")

"""
Vue création d'une nouvelle table de décision — formulaire complet avec
gestion des colonnes, des règles, import/export JSON et enregistrement via API.
"""

import json
import streamlit as st
import requests
from html import escape as _esc
from utils.api import API_BASE, fmt_condition, fmt_output_html, condition_form

_TYPE_LABELS = ["numérique", "texte", "booléen"]
_TYPE_TO_API = {"numérique": "number", "texte": "text", "booléen": "boolean"}
_TYPE_FR     = {"number": "numérique", "text": "texte", "boolean": "booléen"}

_PAGE_CSS = """
<style>
/* ════════════════════════════════════════════════
   PALETTE — bleu ardoise sobre et pro
   --clr-primary   : #4c8c6b  (bleu clair, actions)
   --clr-success   : #059669  (vert, OUT)
   --clr-danger    : #dc2626  (rouge, Enregistrer)
   --clr-surface   : #f8fafc  (fond cartes)
   --clr-border    : #e2e8f0
   --clr-text      : #0f172a
   --clr-muted     : #64748b
════════════════════════════════════════════════ */

/* ── Reset Streamlit natif ── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border: 1.5px solid #e2e8f0 !important;
    background: #ffffff !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.06) !important;
    padding: 1.4rem !important;
}

/* ── Inputs ── */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-baseweb="select"] {
    border-radius: 8px !important;
    border-color: #e2e8f0 !important;
    font-size: 0.9rem !important;
    background: #f8fafc !important;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: #4c8c6b !important;
    background: #fff !important;
    box-shadow: 0 0 0 3px rgba(76,140,107,.12) !important;
}

/* ── BOUTONS GLOBAUX — reset complet ── */
div.stButton > button,
div.stDownloadButton > button {
    border-radius: 8px !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    height: 40px !important;
    min-height: 40px !important;
    padding: 0 18px !important;
    transition: all 0.15s ease !important;
    white-space: nowrap !important;
    letter-spacing: 0.01em !important;
}

/* ── Boutons secondaires (Annuler, Export, Import) ── */
div.stButton > button:not([kind="primary"]),
div.stDownloadButton > button {
    background: #ffffff !important;
    border: 1.5px solid #e2e8f0 !important;
    color: #374151 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,.06) !important;
}
div.stButton > button:not([kind="primary"]):hover,
div.stDownloadButton > button:hover {
    background: #f8fafc !important;
    border-color: #94a3b8 !important;
    color: #111827 !important;
    box-shadow: 0 2px 6px rgba(0,0,0,.08) !important;
}

/* ── Bouton Enregistrer (primary = rouge) ── */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #ef4444, #dc2626) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(220,38,38,.35) !important;
}
div.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #dc2626, #b91c1c) !important;
    box-shadow: 0 4px 14px rgba(220,38,38,.45) !important;
    transform: translateY(-1px) !important;
}

/* ── Hit Policy : cartes radio ── */
div[data-testid="stRadio"] [data-baseweb="radio-group"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
}
div[data-testid="stRadio"] [data-baseweb="radio"] {
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    background: #f8fafc !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
}
div[data-testid="stRadio"] [data-baseweb="radio"]:has(input:checked) {
    border-color: #4c8c6b !important;
    background: #edf7f1 !important;
    box-shadow: 0 0 0 3px rgba(76,140,107,.10) !important;
}
div[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child { display: none !important; }
div[data-testid="stRadio"] [data-baseweb="radio"] p {
    font-weight: 600 !important; color: #0f172a !important; margin: 0 !important; font-size: .92rem !important;
}
div[data-testid="stRadio"] [data-baseweb="radio"] div[data-testid="stCaptionContainer"] p {
    font-size: 0.78rem !important; color: #64748b !important;
    font-weight: 400 !important; margin: 3px 0 0 !important;
}

/* ── Tableau règles — supprime les gaps entre colonnes ── */
[data-testid="stHorizontalBlock"] { gap: 0 !important; }

/* ── Form ajout règle ── */
div[data-testid="stForm"] {
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 1.2rem !important;
    background: #f8fafc !important;
    margin-top: 4px !important;
}

/* ── Divider ── */
hr { border-color: #e2e8f0 !important; margin: 12px 0 !important; }

/* ── Labels inputs ── */
label[data-testid="stWidgetLabel"] p {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #374151 !important;
}
</style>
"""


def _init() -> None:
    """Initialise les clés de session_state utilisées par cette page si elles sont absentes."""
    for k, v in [
        ("nt_columns", []), ("nt_rules", []), ("nt_show_add", False),
        ("nt_show_import", False), ("nt_upload_key", 0),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v


def _cell(content, bg, h="44px", align="left", bb=True):
    """
    Retourne le HTML d'une cellule de tableau de règles.
    Entrées : content — contenu HTML, bg — couleur de fond, h — hauteur,
              align — alignement (left/center), bb — afficher la bordure basse.
    Retour : chaîne HTML de la cellule.
    """
    border_b = "border-bottom:1px solid #e2e8f0;" if bb else ""
    border_r = "border-right:1px solid #e2e8f0;"
    return (
        f'<div style="background:{bg};height:{h};padding:0 14px;'
        f'display:flex;align-items:center;'
        f'justify-content:{"center" if align=="center" else "flex-start"};'
        f'{border_b}{border_r}box-sizing:border-box;overflow:hidden;">'
        f'{content}</div>'
    )


def render() -> None:
    """
    Affiche le formulaire de création de table : informations générales, colonnes,
    tableau de règles éditables, import/export JSON et enregistrement via POST /tables.
    Aucun paramètre, aucun retour.
    """
    _init()
    st.markdown(_PAGE_CSS, unsafe_allow_html=True)

    # ── Breadcrumb ───────────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:.82rem;color:#94a3b8;margin-bottom:6px;font-weight:500;">'
        '<a href="?page=tables" target="_self" style="color:#4c8c6b;text-decoration:none;">Tables</a>'
        ' &nbsp;/&nbsp; Nouvelle table</p>',
        unsafe_allow_html=True,
    )

    # ── Titre + boutons sur la même ligne ────────────────────────────────────
    col_title, col_btns = st.columns([5, 4])
    with col_title:
        st.markdown(
            '<h1 style="font-size:1.9rem;font-weight:800;color:#0f172a;'
            'line-height:1.25;margin:0 0 4px;letter-spacing:-0.02em;">'
            'Créer une table<br>de décision</h1>',
            unsafe_allow_html=True,
        )
    with col_btns:
        st.markdown("<div style='padding-top:24px'></div>", unsafe_allow_html=True)
        # Espace entre boutons via gap sur un flex container HTML
        st.markdown(
            '<div style="display:flex;gap:8px;justify-content:flex-end;align-items:center;">',
            unsafe_allow_html=True,
        )
        b1, b2, b3, b4 = st.columns([1, 1.1, 1.1, 1.4])
        with b1:
            cancel = st.button("✕  Annuler", use_container_width=True, key="btn_cancel")
        with b2:
            st.download_button(
                "↓  Exporter",
                data=json.dumps({
                    "name": st.session_state.get("nt_name", ""),
                    "hit_policy": "FIRST" if st.session_state.get("nt_policy", "First") == "First" else "COLLECT SUM",
                    "columns": st.session_state["nt_columns"],
                    "rules":   st.session_state["nt_rules"],
                }, indent=2, ensure_ascii=False),
                file_name="table.json", mime="application/json",
                use_container_width=True,
                key="btn_export",
            )
        with b3:
            do_import = st.button("↑  Importer", use_container_width=True, key="btn_import")
        with b4:
            save = st.button("✓  Enregistrer", use_container_width=True,
                             type="primary", key="btn_save")
        st.markdown("</div>", unsafe_allow_html=True)

    if cancel:
        for k in ("nt_columns", "nt_rules", "nt_show_add"):
            st.session_state.pop(k, None)
        st.query_params["page"] = "tables"
        st.rerun()

    if do_import:
        st.session_state["nt_show_import"] = not st.session_state["nt_show_import"]

    if st.session_state["nt_show_import"]:
        up = st.file_uploader(
            "Fichier JSON à importer", type="json",
            key=f"nt_upload_{st.session_state['nt_upload_key']}",
        )
        if up:
            try:
                d = json.loads(up.read())
                if "columns" in d: st.session_state["nt_columns"] = d["columns"]
                if "rules"   in d: st.session_state["nt_rules"].extend(d["rules"])
                st.session_state["nt_show_import"] = False
                st.session_state["nt_upload_key"] += 1
                st.rerun()
            except Exception as e:
                st.error(f"Fichier invalide : {e}")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # CARTES — Informations générales  |  Colonnes d'entrée
    # ════════════════════════════════════════════════════════════════════════
    left, _gap, right = st.columns([5, 0.25, 5])

    # ── Carte gauche ─────────────────────────────────────────────────────────
    with left:
        with st.container(border=True):
            st.markdown(
                '<p style="font-size:.95rem;font-weight:700;color:#0f172a;margin:0 0 16px;">'
                '&nbsp; Informations générales</p>',
                unsafe_allow_html=True,
            )
            st.text_input("Nom de la table *", placeholder="ex. Score risque client", key="nt_name")
            st.text_area("Description",
                         placeholder="ex. Calcul du score de risque basé sur le profil client",
                         height=88, key="nt_desc")
            st.markdown(
                '<p style="font-size:.95rem;font-weight:700;color:#0f172a;margin:16px 0 8px;">'
                '&nbsp; Hit Policy *</p>',
                unsafe_allow_html=True,
            )
            st.radio(
                "Hit Policy",
                ["First", "Collect Sum"],
                captions=["Retourne la 1ʳᵉ règle valide", "Additionne toutes les règles"],
                label_visibility="collapsed",
                key="nt_policy",
            )

    # ── Carte droite ──────────────────────────────────────────────────────────
    with right:
        with st.container(border=True):
            st.markdown(
                '<p style="font-size:.95rem;font-weight:700;color:#0f172a;margin:0 0 14px;">'
                '&nbsp; Colonnes d\'entrée (critères)</p>',
                unsafe_allow_html=True,
            )

            # Colonnes déjà ajoutées
            for i, col in enumerate(st.session_state["nt_columns"]):
                ft = _TYPE_FR.get(col["type"], col["type"])
                is_in = col["role"] == "input"
                badge_bg  = "#d4ece0" if is_in else "#dcfce7"
                badge_clr = "#1b3a2f" if is_in else "#059669"
                badge_txt = "IN"      if is_in else "OUT"

                row = st.columns([0.7, 2.8, 1.8, 0.6])
                row[0].markdown(
                    f'<div style="display:flex;align-items:center;height:38px;">'
                    f'<span style="background:{badge_bg};color:{badge_clr};border-radius:5px;'
                    f'padding:3px 8px;font-size:.72rem;font-weight:700;letter-spacing:.04em;">'
                    f'{badge_txt}</span></div>',
                    unsafe_allow_html=True,
                )
                row[1].markdown(
                    f'<div style="display:flex;align-items:center;height:38px;'
                    f'font-size:.9rem;font-weight:500;color:#0f172a;">{col["name"]}</div>',
                    unsafe_allow_html=True,
                )
                row[2].markdown(
                    f'<div style="display:flex;align-items:center;height:38px;'
                    f'font-size:.82rem;color:#64748b;">{ft}</div>',
                    unsafe_allow_html=True,
                )
                if row[3].button("✕", key=f"rc_{i}", help="Supprimer la colonne"):
                    st.session_state["nt_columns"].pop(i)
                    st.rerun()

            # Séparateur
            st.markdown(
                "<div style='border-top:1.5px dashed #e2e8f0;margin:10px 0 12px'></div>",
                unsafe_allow_html=True,
            )

            # Ligne d'ajout — avec labels flottants propres
            st.markdown(
                '<p style="font-size:.78rem;font-weight:600;color:#94a3b8;'
                'text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">'
                'Ajouter une colonne</p>',
                unsafe_allow_html=True,
            )
            add_cols = st.columns([2.8, 2, 1.2, 0.6])
            nn     = add_cols[0].text_input("Nom",   key="nc_n",
                                            label_visibility="collapsed",
                                            placeholder="Nom de la colonne")
            nt_sel = add_cols[1].selectbox("Type",  _TYPE_LABELS, key="nc_t",
                                           label_visibility="collapsed")
            nr     = add_cols[2].selectbox("Rôle",  ["IN", "OUT"], key="nc_r",
                                           label_visibility="collapsed")
            if add_cols[3].button("＋", key="nc_add", help="Ajouter la colonne"):
                if nn.strip():
                    st.session_state["nt_columns"].append({
                        "name": nn.strip(),
                        "type": _TYPE_TO_API[nt_sel],
                        "role": "input" if nr == "IN" else "output",
                    })
                    st.rerun()
                else:
                    st.warning("Donnez un nom à la colonne.")

    # ════════════════════════════════════════════════════════════════════════
    # SECTION — Tableau des règles
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    in_cols  = [c for c in st.session_state["nt_columns"] if c["role"] == "input"]
    out_cols = [c for c in st.session_state["nt_columns"] if c["role"] == "output"]
    rules    = st.session_state["nt_rules"]

    if not in_cols and not out_cols:
        st.markdown(
            '<div style="background:#f0f9f4;border:1.5px dashed #8fbf9f;border-radius:12px;'
            'padding:1.2rem 1.5rem;text-align:center;color:#4c8c6b;font-size:.9rem;">'
            'Ajoutez des colonnes ci-dessus pour commencer à définir vos règles.</div>',
            unsafe_allow_html=True,
        )
    else:
        n_rules = len(rules)
        n_in    = len(in_cols)
        n_out   = len(out_cols)

        # ── En-tête section ──
        st.markdown(
            f'<div style="display:flex;align-items:baseline;gap:12px;margin-bottom:10px;">'
            f'<span style="font-size:1.05rem;font-weight:700;color:#0f172a;">Règles de décision</span>'
            f'<span style="font-size:.8rem;color:#64748b;background:#f1f5f9;'
            f'border-radius:20px;padding:2px 10px;">'
            f'{n_in} critère{"s" if n_in>1 else ""} &nbsp;·&nbsp; '
            f'{n_out} sortie{"s" if n_out>1 else ""} &nbsp;·&nbsp; '
            f'{n_rules} règle{"s" if n_rules!=1 else ""}</span></div>',
            unsafe_allow_html=True,
        )

        all_c = in_cols + out_cols
        W = [0.38] + [2.4] * len(all_c) + [0.45]

        # ── En-tête noms ──
        h = st.columns(W)
        h[0].markdown(_cell(
            "<span style='font-size:.8rem;font-weight:600;color:#94a3b8;'>#</span>",
            "#f8fafc", h="40px", align="center", bb=False), unsafe_allow_html=True)
        for i, c in enumerate(in_cols):
            h[i+1].markdown(_cell(
                f"<span style='font-size:.82rem;font-weight:700;color:#fff;'>{_esc(c['name'])}</span>",
                "#1b3a2f", h="40px", bb=False), unsafe_allow_html=True)
        for i, c in enumerate(out_cols):
            h[len(in_cols)+1+i].markdown(_cell(
                f"<span style='font-size:.82rem;font-weight:700;color:#fff;'>{_esc(c['name'])}</span>",
                "#059669", h="40px", bb=False), unsafe_allow_html=True)
        h[-1].markdown(_cell("", "#f1f5f9", h="40px", bb=False), unsafe_allow_html=True)

        # ── En-tête types ──
        t = st.columns(W)
        t[0].markdown(_cell("", "#eef2f7", h="22px", bb=True), unsafe_allow_html=True)
        for i, c in enumerate(in_cols):
            t[i+1].markdown(_cell(
                f"<span style='font-size:.72rem;color:#8fbf9f;'>{_TYPE_FR.get(c['type'])}</span>",
                "#4c8c6b", h="22px"), unsafe_allow_html=True)
        for i, c in enumerate(out_cols):
            t[len(in_cols)+1+i].markdown(_cell(
                f"<span style='font-size:.72rem;color:#6ee7b7;'>{_TYPE_FR.get(c['type'])}</span>",
                "#10b981", h="22px"), unsafe_allow_html=True)
        t[-1].markdown(_cell("", "#f1f5f9", h="22px"), unsafe_allow_html=True)

        # ── Lignes de règles ──
        del_idx = None
        for idx, rule in enumerate(rules, start=1):
            bg = "#ffffff" if idx % 2 else "#f8fafc"
            d = st.columns(W)
            d[0].markdown(_cell(
                f"<span style='font-size:.82rem;font-weight:600;color:#94a3b8;'>{idx}</span>",
                bg, align="center"), unsafe_allow_html=True)
            for i, c in enumerate(in_cols):
                raw = rule.get("conditions", {}).get(c["name"], "—")
                d[i+1].markdown(_cell(
                    f"<span style='font-size:.88rem;color:#1e293b;'>{fmt_condition(raw)}</span>",
                    bg), unsafe_allow_html=True)
            for i, c in enumerate(out_cols):
                val = rule.get("output", {}).get(c["name"], "—")
                d[len(in_cols)+1+i].markdown(
                    _cell(fmt_output_html(val), bg), unsafe_allow_html=True)
            with d[-1]:
                if st.button("✕", key=f"rd_{idx-1}", help="Supprimer la règle"):
                    del_idx = idx - 1

        if del_idx is not None:
            st.session_state["nt_rules"].pop(del_idx)
            st.rerun()

        # ── Bouton Ajouter règle ──
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        if st.button("＋  Ajouter une règle", use_container_width=True, key="btn_add_rule"):
            st.session_state["nt_show_add"] = not st.session_state["nt_show_add"]
            st.rerun()

        # ── Formulaire ajout règle — clés basées sur INDEX (fix DuplicateKey) ──
        if st.session_state["nt_show_add"]:
            with st.container(border=True):
                conditions: dict = {}
                outputs_v:  dict = {}

                if in_cols:
                    st.markdown(
                        '<p style="font-weight:700;font-size:.92rem;color:#0f172a;margin-bottom:8px;">'
                        'Conditions <span style="font-weight:400;color:#64748b;font-style:italic;">'
                        '(laisser vide = toujours vrai)</span></p>',
                        unsafe_allow_html=True,
                    )
                    fc_list = st.columns(len(in_cols))
                    for ci, (fc, col) in enumerate(zip(fc_list, in_cols)):
                        with fc:
                            st.markdown(
                                f'<p style="font-size:.85rem;font-weight:600;color:#4c8c6b;margin-bottom:4px;">'
                                f'{col["name"]}</p>',
                                unsafe_allow_html=True,
                            )
                            conditions[col["name"]] = condition_form(col, f"ntar_{ci}")

                if out_cols:
                    st.markdown(
                        '<hr style="margin:12px 0;border-color:#e2e8f0;">'
                        '<p style="font-weight:700;font-size:.92rem;color:#0f172a;margin-bottom:8px;">'
                        'Résultats</p>',
                        unsafe_allow_html=True,
                    )
                    oc_list = st.columns(len(out_cols))
                    for oi, (fc, col) in enumerate(zip(oc_list, out_cols)):
                        with fc:
                            if col["type"] == "number":
                                v = st.number_input(col["name"], key=f"nto_{oi}", step=1.0)
                                outputs_v[col["name"]] = str(int(v) if v == int(v) else v)
                            elif col["type"] == "boolean":
                                v = st.selectbox(col["name"], ["true", "false"], key=f"nto_{oi}")
                                outputs_v[col["name"]] = v
                            else:
                                v = st.text_input(col["name"], key=f"nto_{oi}")
                                outputs_v[col["name"]] = v

                if st.button("✓  Ajouter la règle", use_container_width=True, type="primary", key="nt_add_submit"):
                    clean = {k: v for k, v in conditions.items() if v and str(v).strip()}
                    if not all(str(v).strip() for v in outputs_v.values()):
                        st.error("Renseignez tous les champs de résultats.")
                    else:
                        st.session_state["nt_rules"].append(
                            {"conditions": clean, "output": outputs_v}
                        )
                        st.session_state["nt_show_add"] = False
                        st.rerun()

        st.markdown(
            '<p style="font-size:.76rem;color:#94a3b8;margin-top:10px;">'
            "Opérateurs : <code>&gt;</code> <code>&lt;</code> <code>=</code>"
            " <code>!=</code> <code>[a..b]</code> &nbsp;·&nbsp;"
            " Laissez <code>—</code> pour ignorer un critère</p>",
            unsafe_allow_html=True,
        )

    # ── Enregistrer ──────────────────────────────────────────────────────────
    if save:
        name_v   = st.session_state.get("nt_name", "").strip()
        cols     = st.session_state["nt_columns"]
        nt_rules = st.session_state["nt_rules"]
        pol_api  = "FIRST" if st.session_state.get("nt_policy", "First") == "First" else "COLLECT SUM"

        if not name_v:
            st.error("⚠️ Le nom de la table est obligatoire.")
        elif not cols:
            st.error("⚠️ Ajoutez au moins une colonne.")
        elif not any(c["role"] == "input"  for c in cols):
            st.error("⚠️ Ajoutez au moins une colonne d'entrée (IN).")
        elif not any(c["role"] == "output" for c in cols):
            st.error("⚠️ Ajoutez au moins une colonne de sortie (OUT).")
        else:
            try:
                r = requests.post(
                    f"{API_BASE}/tables",
                    json={"name": name_v, "hit_policy": pol_api, "columns": cols},
                    timeout=5,
                )
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
                    st.error(f"Erreur API ({r.status_code}) : {r.text}")
            except Exception as e:
                st.error(f"Impossible de contacter le backend : {e}")
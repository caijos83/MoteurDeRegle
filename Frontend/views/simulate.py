"""
Vue simulation — formulaire de saisie des inputs et affichage du résultat d'évaluation
avec détail règle par règle (match/pas de match) et moteur utilisé.
"""

import time
import streamlit as st
import requests
from html import escape as _esc
from utils.api import api_get, policy_badge_html, fmt_output_html, API_BASE
from Backend.bridge.dmn_matcher import rule_matches as _rule_matches_fn


def _rule_matches(rule: dict, inputs: dict, col_types: dict) -> bool:
    """
    Délègue à dmn_matcher.rule_matches pour colorier les lignes de règles côté IHM.
    Entrées : rule — dict de la règle, inputs — valeurs saisies, col_types — types par colonne.
    Retour : True si toutes les conditions de la règle sont satisfaites.
    """
    return _rule_matches_fn(rule, inputs, col_types)


def _output_num(rule: dict, out_col: str) -> float | None:
    """
    Extrait la valeur numérique de sortie d'une règle pour l'affichage du score.
    Entrées : rule — dict de la règle, out_col — nom de la colonne de sortie.
    Retour : float si la valeur est numérique, None sinon.
    """
    try:
        return float(str(rule["output"].get(out_col, "")).replace("+", ""))
    except Exception:
        return None


# ── Page ──────────────────────────────────────────────────────────────────────

_TYPE_FR = {"number": "numérique", "text": "texte", "boolean": "booléen"}


def render(table_id: str | None = None) -> None:
    """
    Affiche la page de simulation : sélection de la table, saisie des inputs,
    appel à POST /evaluate et affichage du résultat + détail des règles évaluées.
    Entrée : table_id — UUID présélectionné (ou None pour le premier de la liste).
    """
    tables = api_get("/tables") or []
    if not tables:
        st.info("Aucune table disponible.")
        return

    default_idx = 0
    if table_id:
        for i, t in enumerate(tables):
            if t["id"] == table_id:
                default_idx = i
                break

    id_to_table = {t["id"]: t for t in tables}
    selected_id = st.selectbox(
        "Table", options=list(id_to_table.keys()),
        format_func=lambda tid: id_to_table[tid]["name"],
        index=default_idx,
        key="sim_table_selector", label_visibility="collapsed",
    )
    table     = id_to_table[selected_id]
    in_cols   = [c for c in table["columns"] if c["role"] == "input"]
    out_cols  = [c for c in table["columns"] if c["role"] == "output"]
    rules     = table.get("rules", [])
    col_types = {c["name"]: c["type"] for c in table["columns"]}
    policy    = table.get("hit_policy", "FIRST")

    # ── Breadcrumb ────────────────────────────────────────────────────────────
    st.markdown(
        f'<p style="font-size:0.9rem; color:#6b7280; margin-bottom:4px;">'
        f'<a href="?page=tables" target="_self" style="color:#4c8c6b; text-decoration:none;">Tables</a>'
        f' &rsaquo; <a href="?page=detail&table_id={table["id"]}" target="_self" style="color:#4c8c6b; text-decoration:none;">'
        f'{_esc(table["name"])}</a> &rsaquo; Exécution</p>',
        unsafe_allow_html=True,
    )
    st.markdown("## Tester la table")
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    left, right = st.columns([4, 5], gap="large")

    # ── Panneau gauche : saisie ───────────────────────────────────────────────
    with left:
        with st.container(border=True):
            st.markdown("**Valeurs d'entrée**")
            inputs: dict = {}
            for col in in_cols:
                label = f"{col['name']} ({_TYPE_FR.get(col['type'], col['type'])})"
                if col["type"] == "number":
                    v = st.number_input(label, key=f"sim_{col['name']}", step=1.0,
                                        label_visibility="visible")
                    inputs[col["name"]] = v
                elif col["type"] == "boolean":
                    v = st.selectbox(label, ["true", "false"], key=f"sim_{col['name']}")
                    inputs[col["name"]] = v
                else:
                    v = st.text_input(label, key=f"sim_{col['name']}")
                    inputs[col["name"]] = v

            run = st.button("▶  Évaluer", use_container_width=True)  # secondaire = contour

    # ── Panneau droit : résultats ─────────────────────────────────────────────
    with right:
        if not run:
            st.markdown(
                '<div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:10px;'
                ' padding:48px 24px; text-align:center; color:#9ca3af;">'
                '<div style="font-size:2.5rem; margin-bottom:8px;">▶</div>'
                '<div>Renseignez les valeurs et cliquez sur Évaluer</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            t0 = time.perf_counter()
            resp = requests.post(
                f"{API_BASE}/tables/{table['id']}/evaluate",
                json={"inputs": inputs}, timeout=5,
            )
            elapsed_ms = max(1, int((time.perf_counter() - t0) * 1000))

            if not resp.ok:
                st.error(resp.json().get("detail", "Erreur d'évaluation."))
            else:
                api_result = resp.json().get("result")
                policy_label = "Collect Sum" if policy == "COLLECT SUM" else "First"
                out_key = out_cols[0]["name"] if out_cols else "résultat"

                # Valeur d'affichage
                if isinstance(api_result, dict):
                    raw_val = api_result.get(out_key, "")
                    display_val = str(raw_val).strip() if str(raw_val).strip() else None
                elif api_result is not None:
                    display_val = str(api_result)
                else:
                    display_val = None

                engine_label = resp.json().get("engine", "")

                # ── Carte résultat ────────────────────────────────────────────
                if display_val is None:
                    st.warning("Aucune règle ne correspond, ou la valeur de sortie n'a pas été enregistrée.")
                else:
                    try:
                        num = float(display_val.replace("+", ""))
                        disp = f"+{int(num)}" if num > 0 else str(int(num) if num == int(num) else num)
                    except Exception:
                        disp = _esc(display_val)  # échappement HTML pour les valeurs texte

                    st.markdown(
                        f'<div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px;'
                        f' padding:24px 20px; text-align:center; margin-bottom:16px;">'
                        f'<div style="font-size:0.8rem; color:#15803d; font-weight:600; margin-bottom:6px; letter-spacing:.04em;">'
                        f'Résultat — {policy_label}</div>'
                        f'<div style="font-size:3.2rem; font-weight:800; color:#111827; line-height:1;">{disp}</div>'
                        f'<div style="font-size:0.8rem; color:#6b7280; margin-top:6px;">{_esc(out_key)}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # ── Détail des règles ─────────────────────────────────────────
                st.markdown(
                    '<p style="font-weight:600; font-size:0.9rem; margin-bottom:8px;">Détail des règles évaluées</p>',
                    unsafe_allow_html=True,
                )
                first_matched = False
                for idx, rule in enumerate(rules, start=1):
                    matched = _rule_matches(rule, inputs, col_types)

                    if policy == "FIRST" and first_matched:
                        icon, color, status = "✗", "#9ca3af", "ignorée"
                    elif matched:
                        if policy == "FIRST":
                            first_matched = True
                        icon, color = "✓", "#15803d"
                        num_val = _output_num(rule, out_key) if out_cols else None
                        if num_val is not None:
                            sign = "+" if num_val > 0 else ""
                            status = f"match · score {sign}{int(num_val) if num_val == int(num_val) else num_val}"
                        else:
                            ov = rule.get("output", {}).get(out_key, "")
                            status = f"match · {ov}" if ov else "match"
                    else:
                        icon, color, status = "✗", "#9ca3af", "pas de match"

                    row_bg = "#f0fdf4" if icon == "✓" else "#f9fafb"

                    st.markdown(
                        f'<div style="display:flex; align-items:center; gap:10px; padding:8px 12px;'
                        f' border-radius:6px; background:{row_bg}; margin-bottom:4px;">'
                        f'<span style="color:{color}; font-weight:700; font-size:1rem; width:16px; flex-shrink:0;">{icon}</span>'
                        f'<span style="font-size:0.88rem; color:#374151;">'
                        f'Règle {idx}'
                        f' <span style="color:{color};">— {status}</span>'
                        f'</span></div>',
                        unsafe_allow_html=True,
                    )

                engine_display = {
                    "mojo-native":   "Mojo natif",
                    "mojo-docker":   "Mojo Docker",
                    "python-fallback": "Python (fallback)",
                }.get(engine_label, engine_label)
                st.markdown(
                    f'<p style="font-size:0.78rem; color:#9ca3af; margin-top:10px;">'
                    f"Temps d'évaluation : <strong>{elapsed_ms} ms</strong>"
                    + (f" &nbsp;·&nbsp; moteur : {engine_display}" if engine_display else "")
                    + "</p>",
                    unsafe_allow_html=True,
                )

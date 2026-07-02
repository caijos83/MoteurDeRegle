import os
import requests
from html import escape as _html_escape
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

TYPE_OPTIONS   = ["Nombre", "Texte", "Oui / Non"]
TYPE_TO_API    = {"Nombre": "number", "Texte": "text", "Oui / Non": "boolean"}
TYPE_FROM_API  = {"number": "Nombre", "text": "Texte", "boolean": "Oui / Non"}

POLICY_TO_API  = {
    "Première règle applicable":      "FIRST",
    "Additionner tous les résultats": "COLLECT SUM",
}
POLICY_FROM_API = {v: k for k, v in POLICY_TO_API.items()}

# "— (ignorer)" en premier : condition laissée vide = critère ignoré pour cette règle
OPERATORS_NUMBER  = ["— (ignorer)", ">", "<", "≥", "≤", "=", "≠", "entre … et …"]
OPERATORS_TEXT    = ["— (ignorer)", "est égal à", "fait partie de la liste"]
OPERATORS_BOOLEAN = ["— (ignorer)", "est Vrai", "est Faux"]
OP_TO_SYNTAX = {">": ">", "<": "<", "≥": ">=", "≤": "<=", "=": "=", "≠": "!="}


def api_get(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        return r.json() if r.ok else None
    except Exception:
        return None


def fmt_date(raw) -> str:
    """Formate une date ISO en jj/mm/aaaa hh:mm pour l'affichage."""
    if not raw:
        return "—"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "—"


def html_escape(s: str) -> str:
    """Échappe une valeur utilisateur avant injection dans du HTML brut."""
    return _html_escape(str(s))


def fmt_condition(raw: str) -> str:
    """Formate une condition DMN pour l'affichage HTML (sécurisé)."""
    if not raw or raw == "—":
        return "—"
    raw = str(raw).strip()
    # Échappement HTML d'abord (< → &lt;, > → &gt;, & → &amp;, etc.)
    raw = _html_escape(raw)
    # Puis remplacement des séquences d'opérateurs DMN par des symboles Unicode
    raw = raw.replace("&gt;=", "≥").replace("&lt;=", "≤").replace("!=", "≠")
    return raw


def fmt_output_html(val: str) -> str:
    """Affiche une valeur de sortie : colorée si numérique, échappée sinon."""
    try:
        num = float(str(val).replace("+", ""))
        disp = f"+{int(num)}" if num > 0 else (str(int(num)) if num == int(num) else str(num))
        color = "#16a34a" if num > 0 else ("#dc2626" if num < 0 else "#374151")
        return f'<span style="color:{color}; font-weight:600;">{disp}</span>'
    except Exception:
        return _html_escape(str(val))


def policy_badge_html(policy: str) -> str:
    if policy == "FIRST":
        return (
            '<span style="background:#dbeafe; color:#1d4ed8; border-radius:20px;'
            ' padding:3px 12px; font-size:0.78em; font-weight:600;">First</span>'
        )
    return (
        '<span style="background:#dcfce7; color:#166534; border-radius:20px;'
        ' padding:3px 12px; font-size:0.78em; font-weight:600;">Collect Sum</span>'
    )


def score_range(table: dict) -> str:
    if table.get("hit_policy") != "COLLECT SUM":
        return "—"
    out_cols = [c for c in table.get("columns", []) if c["role"] == "output" and c["type"] == "number"]
    if not out_cols:
        return "—"
    key = out_cols[0]["name"]
    vals = []
    for rule in table.get("rules", []):
        try:
            vals.append(float(str(rule["output"].get(key, "")).replace("+", "")))
        except Exception:
            pass
    if not vals:
        return "—"
    mn, mx = int(min(vals)), int(max(vals))
    return f"{mn}→+{mx}" if mx > 0 else f"{mn}→{mx}"


def build_condition(col_type: str, operator: str, value, value2="") -> str:
    if not operator or operator == "— (ignorer)":
        return ""
    if col_type == "number":
        if operator == "entre … et …":
            v1 = int(value) if isinstance(value, float) and value == int(value) else value
            v2 = int(value2) if isinstance(value2, float) and value2 == int(value2) else value2
            return f"[{v1}..{v2}]"
        v = int(value) if isinstance(value, float) and value == int(value) else value
        return f"{OP_TO_SYNTAX[operator]} {v}"
    if col_type == "text":
        if operator == "fait partie de la liste":
            items = [v.strip() for v in str(value).split(",") if v.strip()]
            return '["' + '","'.join(items) + '"]'
        return str(value)
    if col_type == "boolean":
        return "true" if operator == "est Vrai" else "false"
    return str(value)


def condition_form(col: dict, key_prefix: str) -> str:
    """
    Widget de saisie d'une condition DMN pour un formulaire Streamlit.

    IMPORTANT — compatibilité st.form : à l'intérieur d'un formulaire Streamlit,
    les interactions sur les widgets ne déclenchent pas de rechargement de page.
    Pour l'opérateur numérique "entre … et …", les deux bornes (v1 et v2) sont
    TOUJOURS rendues, qu'elles soient utilisées ou non. Ainsi les clés de widget
    restent stables et l'utilisateur n'a pas à re-sélectionner l'opérateur après soumission.
    """
    import streamlit as st
    ct = col["type"]

    if ct == "number":
        op = st.selectbox("Opérateur", OPERATORS_NUMBER, key=f"{key_prefix}_op")
        # Les deux champs sont toujours affichés — seule façon de fonctionner
        # dans un st.form (pas de rerun mid-form).
        # build_condition ignore v2 pour tous les opérateurs sauf "entre … et …".
        v1 = st.number_input(
            "Valeur" if op != "entre … et …" else "De (borne basse)",
            key=f"{key_prefix}_v1", step=1.0,
        )
        v2 = st.number_input(
            "À (borne haute)",
            key=f"{key_prefix}_v2", step=1.0,
            help="Requis uniquement pour l'opérateur 'entre … et …'",
        )
        return build_condition(ct, op, v1, v2)

    if ct == "text":
        op = st.selectbox("Opérateur", OPERATORS_TEXT, key=f"{key_prefix}_op")
        if op == "— (ignorer)":
            return ""
        v = st.text_input(
            "Valeurs (séparées par des virgules)" if op == "fait partie de la liste" else "Valeur",
            key=f"{key_prefix}_v",
        )
        return build_condition(ct, op, v)

    if ct == "boolean":
        op = st.selectbox("Valeur", OPERATORS_BOOLEAN, key=f"{key_prefix}_op")
        return build_condition(ct, op, "")

    return ""

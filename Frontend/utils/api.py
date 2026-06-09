import requests

API_BASE = "http://localhost:8000/api/v1"

TYPE_OPTIONS   = ["Nombre", "Texte", "Oui / Non"]
TYPE_TO_API    = {"Nombre": "number", "Texte": "text", "Oui / Non": "boolean"}
TYPE_FROM_API  = {"number": "Nombre", "text": "Texte", "boolean": "Oui / Non"}

POLICY_TO_API  = {
    "Première règle applicable":      "FIRST",
    "Additionner tous les résultats": "COLLECT SUM",
}
POLICY_FROM_API = {v: k for k, v in POLICY_TO_API.items()}

OPERATORS_NUMBER  = [">", "<", "≥", "≤", "=", "≠", "entre … et …"]
OPERATORS_TEXT    = ["est égal à", "fait partie de la liste"]
OPERATORS_BOOLEAN = ["est Vrai", "est Faux"]
OP_TO_SYNTAX = {">": ">", "<": "<", "≥": ">=", "≤": "<=", "=": "=", "≠": "!="}


def api_get(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        return r.json() if r.ok else None
    except Exception:
        return None


def fmt_condition(raw: str) -> str:
    if not raw or raw == "—":
        return "—"
    raw = str(raw).strip()
    raw = raw.replace(">= ", "≥ ").replace("<= ", "≤ ").replace("!= ", "≠ ")
    return raw


def fmt_output_html(val: str) -> str:
    try:
        num = float(str(val).replace("+", ""))
        disp = f"+{int(num)}" if num > 0 else (str(int(num)) if num == int(num) else str(num))
        color = "#16a34a" if num > 0 else ("#dc2626" if num < 0 else "#374151")
        return f'<span style="color:{color}; font-weight:600;">{disp}</span>'
    except Exception:
        return str(val)


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


def build_condition(col_type, operator, value, value2=""):
    if col_type == "number":
        if operator == "entre … et …":
            return f"[{value}..{value2}]"
        return f"{OP_TO_SYNTAX[operator]} {value}"
    if col_type == "text":
        if operator == "fait partie de la liste":
            items = [v.strip() for v in value.split(",")]
            return '["' + '","'.join(items) + '"]'
        return value
    if col_type == "boolean":
        return "true" if operator == "est Vrai" else "false"
    return value


def condition_form(col, key_prefix):
    import streamlit as st
    ct = col["type"]
    if ct == "number":
        op = st.selectbox("Opérateur", OPERATORS_NUMBER, key=f"{key_prefix}_op")
        if op == "entre … et …":
            c1, c2 = st.columns(2)
            v1 = c1.number_input("De", key=f"{key_prefix}_v1", step=1.0)
            v2 = c2.number_input("À",  key=f"{key_prefix}_v2", step=1.0)
            return build_condition(ct, op, v1, v2)
        v = st.number_input("Valeur", key=f"{key_prefix}_v", step=1.0)
        return build_condition(ct, op, v)
    if ct == "text":
        op = st.selectbox("Opérateur", OPERATORS_TEXT, key=f"{key_prefix}_op")
        v = st.text_input(
            "Valeurs séparées par des virgules" if op == "fait partie de la liste" else "Valeur",
            key=f"{key_prefix}_v",
        )
        return build_condition(ct, op, v)
    if ct == "boolean":
        op = st.selectbox("Valeur", OPERATORS_BOOLEAN, key=f"{key_prefix}_op")
        return build_condition(ct, op, "")
    return ""

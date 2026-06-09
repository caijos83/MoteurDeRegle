import streamlit as st
import requests
from utils.api import api_get, policy_badge_html, fmt_output_html, API_BASE


def render(table_id: str | None = None) -> None:
    tables = api_get("/tables") or []
    if not tables:
        st.info("Aucune table disponible.")
        return

    table_map = {t["name"]: t for t in tables}
    default_idx = 0
    if table_id:
        for i, t in enumerate(tables):
            if t["id"] == table_id:
                default_idx = i
                break

    selected_name = st.selectbox("Table", list(table_map.keys()), index=default_idx)
    table = table_map[selected_name]
    input_cols = [c for c in table["columns"] if c["role"] == "input"]

    # ── Breadcrumb ────────────────────────────────────────────────────────────
    st.markdown(
        f'<p style="font-size:0.9rem; color:#6b7280;">'
        f'<a href="?page=tables" style="color:#4f46e5; text-decoration:none;">Tables</a>'
        f' &rsaquo; <a href="?page=detail&table_id={table["id"]}" style="color:#4f46e5; text-decoration:none;">{table["name"]}</a>'
        f" &rsaquo; Simuler</p>",
        unsafe_allow_html=True,
    )
    st.markdown(f"## Simuler — {table['name']}")
    st.markdown(policy_badge_html(table["hit_policy"]), unsafe_allow_html=True)
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # ── Input form ────────────────────────────────────────────────────────────
    with st.form("simulate", border=True):
        st.subheader("Valeurs à tester")
        inputs: dict = {}
        for col in input_cols:
            label = col["name"]
            if col["type"] == "number":
                v = st.number_input(label, key=f"sim_{col['name']}", step=1.0)
                inputs[col["name"]] = v
            elif col["type"] == "boolean":
                v = st.selectbox(label, ["Vrai", "Faux"], key=f"sim_{col['name']}")
                inputs[col["name"]] = "true" if v == "Vrai" else "false"
            else:
                v = st.text_input(label, key=f"sim_{col['name']}")
                inputs[col["name"]] = v

        run = st.form_submit_button("▶  Obtenir la décision", use_container_width=True, type="primary")

    if run:
        resp = requests.post(
            f"{API_BASE}/tables/{table['id']}/evaluate",
            json={"inputs": inputs},
            timeout=5,
        )
        if resp.ok:
            data = resp.json()
            result = data.get("result")
            nb_matched = data.get("matched_rules")

            st.divider()
            st.subheader("Résultat")

            if result is None:
                st.warning("Aucune règle ne correspond aux valeurs saisies.")
            elif isinstance(result, dict):
                cols = st.columns(len(result))
                for col, (k, v) in zip(cols, result.items()):
                    col.markdown(
                        f'<div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:20px; text-align:center;">'
                        f'<div style="font-size:1.6rem; font-weight:700;">{fmt_output_html(str(v))}</div>'
                        f'<div style="font-size:0.82rem; color:#6b7280; margin-top:4px;">{k}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                output_cols = [c for c in table["columns"] if c["role"] == "output"]
                label = output_cols[0]["name"] if output_cols else "Résultat"
                st.markdown(
                    f'<div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:20px; text-align:center; max-width:200px;">'
                    f'<div style="font-size:1.6rem; font-weight:700;">{fmt_output_html(str(result))}</div>'
                    f'<div style="font-size:0.82rem; color:#6b7280; margin-top:4px;">{label}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

            if nb_matched is not None:
                st.caption(f"{nb_matched} règle(s) appliquée(s).")
        else:
            detail = resp.json().get("detail", "Erreur inconnue.")
            st.error(f"Impossible d'évaluer : {detail}")

"""
Page API — documentation des interfaces REST, GraphQL et MCP du moteur DMN.
"""

import streamlit as st
from utils.api import api_get, API_BASE


def render() -> None:
    """
    Affiche la documentation des trois interfaces API : REST (table des endpoints),
    GraphQL (exemples query/mutation) et MCP (liste des outils IA exposés).
    Aucun paramètre, aucun retour.
    """
    st.markdown("## Interface API")
    st.markdown(
        '<p style="color:#6b7280;font-size:.95rem;margin-top:-8px;margin-bottom:24px;">'
        "Toutes les fonctionnalités du moteur DMN sont accessibles via trois interfaces."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Statut ────────────────────────────────────────────────────────────────
    health = api_get("/health".replace("/api/v1", "").replace(API_BASE, "")) or api_get("")
    # Tente /health directement
    import requests, os
    base_root = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1").rsplit("/api", 1)[0]
    try:
        h = requests.get(f"{base_root}/health", timeout=2)
        api_ok = h.ok
    except Exception:
        api_ok = False

    status_color = "#16a34a" if api_ok else "#dc2626"
    status_text  = "En ligne" if api_ok else "Hors ligne"
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:8px;'
        f'background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
        f'padding:8px 16px;margin-bottom:24px;">'
        f'<span style="width:8px;height:8px;border-radius:50%;'
        f'background:{status_color};display:inline-block;"></span>'
        f'<span style="font-size:.88rem;color:#374151;">API REST — '
        f'<strong style="color:{status_color};">{status_text}</strong>'
        f' · <code style="font-size:.82rem;">{base_root}</code></span>'
        f"</div>",
        unsafe_allow_html=True,
    )

    tab_rest, tab_graphql, tab_mcp = st.tabs(["REST API", "GraphQL", "MCP (Agents IA)"])

    # ── REST ──────────────────────────────────────────────────────────────────
    with tab_rest:
        st.markdown(
            f"Documentation interactive (Swagger UI) : "
            f"[{base_root}/docs]({base_root}/docs)"
        )
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        endpoints = [
            ("GET",    "/tables",                 "Lister toutes les tables"),
            ("GET",    "/tables/{id}",            "Obtenir une table par identifiant"),
            ("POST",   "/tables",                 "Créer une table (201)"),
            ("PUT",    "/tables/{id}",            "Modifier une table (colonnes, règles, hit policy)"),
            ("DELETE", "/tables/{id}",            "Supprimer une table (204)"),
            ("POST",   "/tables/{id}/evaluate",   "Évaluer des valeurs d'entrée"),
            ("GET",    "/health",                 "Vérifier l'état du service"),
        ]

        method_color = {
            "GET":    ("#1b3a2f", "#d4ece0"),
            "POST":   ("#166534", "#dcfce7"),
            "PUT":    ("#92400e", "#fef3c7"),
            "DELETE": ("#991b1b", "#fee2e2"),
        }

        th = "padding:8px 14px;font-size:.8rem;font-weight:600;color:#6b7280;text-transform:uppercase;background:#f8fafc;"
        td = "padding:10px 14px;font-size:.88rem;border-bottom:1px solid #f3f4f6;"

        rows = ""
        for method, path, desc in endpoints:
            clr, bg = method_color.get(method, ("#374151", "#f8fafc"))
            badge = (
                f'<span style="background:{bg};color:{clr};border-radius:4px;'
                f'padding:3px 8px;font-size:.75rem;font-weight:700;'
                f'font-family:monospace;">{method}</span>'
            )
            rows += f"<tr><td style='{td}'>{badge}</td><td style='{td}'><code>/api/v1{path}</code></td><td style='{td}'>{desc}</td></tr>"

        st.markdown(
            f'<div style="overflow-x:auto;border:1px solid #e5e7eb;border-radius:8px;">'
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr>'
            f'<th style="{th}">Méthode</th><th style="{th}">Endpoint</th><th style="{th}">Description</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        st.markdown("**Format JSON — table de décision**")
        st.code("""{
  "id": "uuid",
  "name": "EligibiliteCredit",
  "hit_policy": "FIRST",
  "columns": [
    {"name": "age",      "type": "number",  "role": "input"},
    {"name": "revenu",   "type": "number",  "role": "input"},
    {"name": "decision", "type": "text",    "role": "output"}
  ],
  "rules": [
    {"conditions": {"age": ">= 18", "revenu": ">= 2000"}, "output": {"decision": "ACCEPTE"}},
    {"conditions": {"age": "<  18"},                       "output": {"decision": "REFUSE"}}
  ]
}""", language="json")

    # ── GraphQL ───────────────────────────────────────────────────────────────
    with tab_graphql:
        st.markdown(
            f"Interface GraphiQL (test interactif) : "
            f"[{base_root}/graphql]({base_root}/graphql)"
        )
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        col_q, col_m = st.columns(2)
        with col_q:
            st.markdown("**Queries**")
            st.code("""query {
  tables { id name hitPolicy }
  table(id: "uuid") { name rules { conditions output } }
  columnTypes
}""", language="graphql")
        with col_m:
            st.markdown("**Mutations**")
            st.code("""mutation {
  createTable(input: { name: "...", hitPolicy: "FIRST", columns: [] }) { id }
  deleteTable(id: "uuid")
  evaluateTable(tableId: "uuid", inputsJson: "{\"age\": \"25\"}") { result }
}""", language="graphql")

    # ── MCP ───────────────────────────────────────────────────────────────────
    with tab_mcp:
        st.markdown(
            "Le serveur MCP expose le moteur DMN comme **outils IA** — "
            "tout agent compatible (Claude Desktop, VS Code Copilot, etc.) peut l'utiliser "
            "directement en langage naturel, sans modification côté client."
        )
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        tools = [
            ("dmn_list_tables",    "Lister toutes les tables"),
            ("dmn_get_table",      "Obtenir une table par identifiant"),
            ("dmn_create_table",   "Créer une table (nom, hit_policy, colonnes)"),
            ("dmn_add_column",     "Ajouter une colonne à une table"),
            ("dmn_add_rule",       "Ajouter une règle à une table"),
            ("dmn_evaluate",       "Évaluer des inputs contre une table"),
            ("dmn_delete_table",   "Supprimer une table"),
            ("dmn_get_column_types", "Obtenir les types de colonnes supportés"),
        ]

        td2 = "padding:9px 14px;font-size:.88rem;border-bottom:1px solid #f3f4f6;"
        rows2 = "".join(
            f"<tr><td style='{td2}'><code>{name}</code></td><td style='{td2}'>{desc}</td></tr>"
            for name, desc in tools
        )
        st.markdown(
            f'<div style="overflow-x:auto;border:1px solid #e5e7eb;border-radius:8px;">'
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr><th style="{th}">Outil</th><th style="{th}">Description</th></tr></thead>'
            f'<tbody>{rows2}</tbody></table></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        st.markdown("**Lancer le serveur MCP**")
        st.code("python API/mcp/server.py", language="bash")
        st.caption(
            "Configuration Claude Desktop / VS Code : voir `API/mcp/README.md`"
        )

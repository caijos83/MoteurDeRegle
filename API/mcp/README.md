# DMN Light — Serveur MCP

## Qu'est-ce que MCP ?

MCP (Model Context Protocol) est un standard ouvert créé par Anthropic (2024, Apache 2.0).
Il permet à n'importe quel agent IA de se connecter à des outils via une interface standard,
comme un port USB : un seul serveur, compatible avec tous les clients.

Clients compatibles : Claude Desktop, VS Code Copilot, Cursor, Zed, tout agent MCP.

## Lancer le serveur

```bash
python API/mcp/server.py
```

Le serveur tourne en **stdio** (entrée/sortie standard) — aucun port réseau, 100% local.

## Configuration Claude Desktop

Ajouter dans `%APPDATA%\Claude\claude_desktop_config.json` (Windows) :

```json
{
  "mcpServers": {
    "dmn-light": {
      "command": "python",
      "args": ["C:/chemin/vers/MoteurDeRegle/API/mcp/server.py"]
    }
  }
}
```

## Configuration VS Code (avec extension MCP)

```json
{
  "mcp.servers": {
    "dmn-light": {
      "command": "python",
      "args": ["${workspaceFolder}/API/mcp/server.py"]
    }
  }
}
```

## Outils exposés

| Outil                  | Description                                    |
|------------------------|------------------------------------------------|
| `dmn_get_column_types` | Types de colonnes supportés                    |
| `dmn_list_tables`      | Lister toutes les tables                       |
| `dmn_get_table`        | Obtenir une table par id                       |
| `dmn_create_table`     | Créer une table (nom, hit_policy, colonnes)    |
| `dmn_add_column`       | Ajouter une colonne à une table                |
| `dmn_add_rule`         | Ajouter une règle (conditions + output)        |
| `dmn_evaluate`         | Évaluer des inputs → décision ou score         |
| `dmn_delete_table`     | Supprimer une table                            |

## Exemple d'utilisation via Claude

Une fois le serveur MCP configuré, vous pouvez demander à Claude :

> "Crée une table de décision 'EligibiliteCredit' avec hit policy FIRST,
>  colonnes age (number, input) et revenu (number, input), decision (text, output).
>  Ajoute une règle : si age >= 18 et revenu >= 2000 alors decision = ACCEPTE.
>  Évalue avec age=25, revenu=3000."

Claude appellera automatiquement les outils MCP pour réaliser ces opérations.

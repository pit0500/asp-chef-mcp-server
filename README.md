# ASP Chef MCP Server

Collega **Claude Desktop** (o qualsiasi client MCP) ad **ASP Chef** (https://asp-chef.alviano.net).

## Architettura

```
Claude Desktop
    │  STDIO (MCP protocol)
    ▼
asp-chef-mcp (FastMCP)
    │  asyncio Queue
    ▼
FastAPI HTTP server  ──► GET /events  (SSE stream → browser)
                     ◄── POST /sync   (recipe snapshot ← browser)

Browser (ASP Chef)
    └─ MCPServer.svelte  ──SSE──► riceve comandi → chiama Recipe.*()
                         ──POST /sync──► invia stato corrente
```

Il processo è **unico**: FastMCP (STDIO) e FastAPI (HTTP:8000) girano
nello stesso processo Python. FastAPI gira in un thread daemon separato.

---

## Installazione

### 1. Prerequisiti

- Python ≥ 3.11
- `uv` (consigliato) oppure `pip`

### 2. Clona / scarica questo progetto

```bash
git clone <questo-repo>   # oppure estrai lo zip
cd asp-chef-mcp
```

### 3. Crea il virtualenv e installa

```bash
# Con uv (consigliato):
uv venv
uv pip install -e .

# Con pip:
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .
```

### 4. Configura Claude Desktop

Apri (o crea) il file di configurazione di Claude Desktop:

| OS      | Percorso                                                                 |
|---------|--------------------------------------------------------------------------|
| macOS   | `~/Library/Application Support/Claude/claude_desktop_config.json`        |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json`                            |
| Linux   | `~/.config/Claude/claude_desktop_config.json`                            |

Aggiungi questa sezione (adatta i percorsi al tuo sistema):

#### Con `uv` (consigliato):

```json
{
  "mcpServers": {
    "asp-chef": {
      "command": "uv",
      "args": [
        "run",
        "--project", "/percorso/assoluto/asp-chef-mcp",
        "asp-chef-mcp"
      ]
    }
  }
}
```

#### Con Python diretto:

```json
{
  "mcpServers": {
    "asp-chef": {
      "command": "/percorso/assoluto/asp-chef-mcp/.venv/bin/python",
      "args": ["-m", "asp_chef_mcp.server"]
    }
  }
}
```

> **Windows**: usa backslash e `.venv\Scripts\python.exe`.

### 5. Riavvia Claude Desktop

Dopo aver salvato il file di configurazione, riavvia completamente Claude Desktop.
Dovresti vedere il tool 🔨 nella barra degli strumenti con "asp-chef" disponibile.

---

## Uso con ASP Chef

1. Apri https://asp-chef.alviano.net nel browser.
2. Aggiungi l'operazione **MCP Server** alla ricetta (appare nella lista delle operazioni).
3. Assicurati che l'URL sia `http://localhost:8000` e premi **Connect**.
4. In Claude Desktop scrivi ad esempio:

   > "Aggiungi un'operazione Search Models che cerca tutti i modelli di un programma
   >  con i fatti `a. b. c.` e stampa i risultati."

Claude chiamerà automaticamente i tool MCP e il browser aggiornerà la ricetta in tempo reale.

---

## Endpoint HTTP

| Metodo | Path       | Descrizione                                        |
|--------|------------|----------------------------------------------------|
| GET    | `/events`  | SSE stream – il browser si connette qui            |
| POST   | `/sync`    | Il browser invia lo stato corrente della ricetta   |
| GET    | `/health`  | Healthcheck JSON                                   |

---

## Sviluppo

Per testare il server senza Claude Desktop, usa l'**MCP Inspector**:

```bash
# Installa l'inspector (richiede Node.js)
npx @modelcontextprotocol/inspector uv run --project . asp-chef-mcp
```

Si aprirà una UI web su http://localhost:5173 dove puoi chiamare i tool manualmente.

---

## Tool MCP disponibili

| Tool                    | Descrizione                                               |
|-------------------------|-----------------------------------------------------------|
| `get_recipe`            | Legge lo stato attuale della ricetta                      |
| `get_operation_catalogue` | Catalogo di tutte le operazioni disponibili             |
| `add_operation`         | Aggiunge un'operazione alla pipeline                      |
| `remove_operation`      | Rimuove un'operazione per indice                          |
| `remove_all_operations` | Svuota la ricetta                                         |
| `edit_operation`        | Modifica le opzioni di un'operazione esistente            |
| `swap_operations`       | Scambia due operazioni di posizione                       |
| `duplicate_operation`   | Duplica un'operazione                                     |
| `remove_operations`     | Rimuove una sequenza di operazioni                        |
| `toggle_apply`          | Attiva/disattiva un'operazione                            |
| `toggle_stop`           | Attiva/disattiva il breakpoint dopo un'operazione         |
| `toggle_show`           | Mostra/nasconde l'output di un'operazione                 |
| `fix_operation`         | Cambia il tipo di un'operazione esistente                 |
| `build_asp_pipeline`    | Suggerisce un piano di operazioni da una descrizione      |

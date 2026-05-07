# ASP Chef MCP Server

Connect **Claude Desktop** (or any MCP client) to **ASP Chef** (https://asp-chef.alviano.net).

## Architecture

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
    └─ MCPServer.svelte  ──SSE──► receives commands → calls Recipe.*()
                         ──POST /sync──► sends current state
```

The process is **single**: FastMCP (STDIO) and FastAPI (HTTP:8000) run in the same Python process. FastAPI runs in a separate daemon thread.

---

## Installation

### 1. Prerequisites

- Python ≥ 3.11
- `uv` (recommended) or `pip`

### 2. Clone / download this project

```bash
git clone <this-repo>   # or extract the zip
cd asp-chef-mcp
```

### 3. Create virtualenv and install

```bash
# With uv (recommended):
uv venv
uv pip install -e .

# With pip:
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .
```

### 4. Configure Claude Desktop

Open (or create) the Claude Desktop configuration file:

| OS      | Path                                                                     |
|---------|--------------------------------------------------------------------------|
| macOS   | `~/Library/Application Support/Claude/claude_desktop_config.json`        |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json`                            |
| Linux   | `~/.config/Claude/claude_desktop_config.json`                            |

Add this section (adjust the paths to your system):

#### With `uv` (recommended):

```json
{
  "mcpServers": {
    "asp-chef": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/asp-chef-mcp-server/src/asp_chef_mcp_server",
        "run",
        "server.py",
        "--port",
        "8000"
      ]
    }
  }
}
```

> **Note**: The `--port` argument is optional (defaults to 8000). You only need it if you want to run on a different port.

---

## Other MCP Clients

This server is compatible with any client supporting the Model Context Protocol. Check the official documentation for setup instructions:

- [**Gemini CLI**](https://geminicli.com/docs/mcp)
- [**OpenAI Codex**](https://developers.openai.com/codex/mcp)
- [**Goose**](https://goose-docs.ai/docs/tutorials/custom-extensions/)

---

### 5. Restart your client

After saving the configuration file, completely restart your MCP client (e.g. Claude Desktop).
You should see the tool available.

---

## Usage with ASP Chef

1. Open https://asp-chef.alviano.net in your browser.
2. Add the **MCP Server** operation to the recipe (it appears in the operations list).
3. Ensure the URL is `http://localhost:{PORT}` and press **Connect**.
4. In Claude Desktop, you can write for example:

   > "Add a Search Models operation that finds all models of a program with facts `a. b. c.` and prints the results."

Claude will automatically call the MCP tools, and the browser will update the recipe in real-time.

---

## HTTP Endpoints

| Method | Path       | Description                                        |
|--------|------------|----------------------------------------------------|
| GET    | `/events`  | SSE stream – the browser connects here            |
| POST   | `/sync`    | The browser sends the current recipe state         |
| POST   | `/docs`    | The browser sends the documentation for operations |
| GET    | `/health`  | JSON healthcheck                                   |

---

## Available MCP Tools

| Tool                          | Description                                                                 |
|-------------------------------|-----------------------------------------------------------------------------|
| `get_recipe`                  | Get the current state of the ASP Chef recipe pipeline.                      |
| `get_operation_docs`          | Get detailed documentation and options schema for a specific operation.     |
| `search_operations`           | Search for operations matching a keyword in name or documentation.          |
| `get_operation_catalogue`     | Explore available tools grouped alphabetically.                             |
| `set_input`                   | Set the input text for the pipeline (with optional encoding).               |
| `set_global_option`           | Set a global option (e.g., auto-run).                                       |
| `add_operation`               | Add an operation to the pipeline at a specific index.                       |
| `remove_operation`            | Remove an operation at a specific index.                                    |
| `remove_all_operations`       | Clear the entire recipe.                                                    |
| `edit_operation`              | Update an operation's options (requires full replacement).                  |
| `swap_operations`             | Swap the positions of two operations.                                       |
| `duplicate_operation`         | Duplicate an operation at a specific index.                                 |
| `remove_operations`           | Remove a range or all operations starting from an index.                    |
| `toggle_apply`                | Enable or disable an operation.                                             |
| `toggle_stop`                 | Enable or disable a breakpoint after an operation.                          |
| `toggle_show`                 | Show or hide the output of an operation.                                    |
| `fix_operation`               | Change the type of an existing operation.                                   |
| `toggle_readonly_operation`   | Toggle the read-only state of an operation.                                 |
| `toggle_hide_header_operation`| Toggle the visibility of an operation's header.                             |
| `build_asp_pipeline`          | Suggest a pipeline plan based on a description.                             |

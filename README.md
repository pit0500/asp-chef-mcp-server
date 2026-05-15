# ASP Chef MCP Server

Connect **any MCP client** to **ASP Chef** (https://asp-chef.alviano.net).

The server also exposes a local ASP syntax manual backed by markdown, so an LLM can
consult structured clingo guidance instead of relying only on its parametric memory.

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

The bundled manual assets live in `src/asp_chef_mcp_server/clingo_manual/`:

- `guide.pdf`: original local reference
- `guide.md`: retrieval-friendly companion used by MCP tools
- `asp-clingo-syntax.SKILL.md`: flat skill entry point for syntax-safe ASP/clingo code
- `asp-modeling-patterns.SKILL.md`: flat skill entry point for common ASP modeling families
- `asp-pattern-*.md`: reusable problem-pattern references for common encodings

The process is **single**: FastMCP (STDIO) and FastAPI (HTTP:8100) run in the same Python process. FastAPI runs in a separate daemon thread.

---

## Installation

### 1. Prerequisites

- Python ≥ 3.11
- `uv` (recommended) or `pip`

### 2. Clone / download this project

```bash
git clone <this-repo>   # or extract the zip
cd asp-chef-mcp-server
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
        "/absolute/path/to/asp-chef-mcp-server",
        "run",
        "asp-chef-mcp",
        "--host",
        "localhost",
        "--port",
        "8100"
      ]
    }
  }
}
```

> **Note**: The `--port` and `--host` arguments are optional (defaults to `127.0.0.1:8100`). You only need them if you want to run on a different port or host.

#### With an installed console script

After `uv pip install -e .` or `pip install -e .`, the package exposes an `asp-chef-mcp`
entrypoint. If your client can use binaries from the virtualenv directly, you can configure:

```json
{
  "mcpServers": {
    "asp-chef": {
      "command": "/absolute/path/to/asp-chef-mcp-server/.venv/bin/asp-chef-mcp",
      "args": [
        "--host",
        "localhost",
        "--port",
        "8100"
      ]
    }
  }
}
```

You can also run it manually:

```bash
uv run asp-chef-mcp --host localhost --port 8100
```

or:

```bash
python -m asp_chef_mcp_server --host localhost --port 8100
```

> **Note**: The `--port` and `--host` arguments are optional (defaults to `127.0.0.1:8100`).

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
2. Add the **MCP AI Assistant** operation to the recipe (it appears in the operations list).
3. Ensure the URL is `http://{HOST}:{PORT}` and press **Connect**.
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
| `list_asp_manual_sections`    | List the sections in the local ASP syntax manual markdown.                  |
| `get_asp_manual_section`      | Return one named section from the local ASP syntax manual.                  |
| `search_asp_manual`           | Search the local ASP syntax manual for clingo constructs.                   |
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

## ASP Manual Layer

The server includes a local ASP syntax layer intended to reduce hallucinations when
an LLM is asked about clingo or Answer Set Programming syntax.

### How it works

- The system prompt instructs the model to consult the manual before answering syntax-sensitive questions.
- `search_asp_manual(query)` performs local retrieval over `guide.md`.
- `get_asp_manual_section(section_name)` returns the full section body for a specific topic.
- `list_asp_manual_sections()` exposes the available structure so the client can browse it.

### Current source of truth

The markdown companion is intentionally easy to search and maintain. It is not meant
to replace the full upstream guide:

- prefer `guide.md` for retrieval by the LLM
- keep `guide.pdf` as the fuller local reference
- extend `guide.md` over time with additional sections when you observe recurring syntax mistakes

### Recommended usage

For questions involving rules, negation, choices, aggregates, optimization,
`#show`, `#program`, or variable safety, the MCP client should call the ASP manual
tools before generating a final answer or writing ASP code.

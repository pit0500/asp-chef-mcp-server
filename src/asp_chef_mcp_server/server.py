"""
ASP Chef MCP Server
===================
Dual-transport server:
  • STDIO  → Claude Desktop (MCP protocol via FastMCP)
  • HTTP   → ASP Chef browser UI (SSE commands + /sync endpoint via FastAPI)

Architecture
------------
Claude Desktop  ──STDIO──►  FastMCP (MCP tools)
                                │
                                │  asyncio.Queue (command bus)
                                │
ASP Chef UI  ◄──SSE────  FastAPI  ◄──POST /sync──  ASP Chef UI
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastmcp import FastMCP

from asp_chef_docs import ASP_CHEF_DOCS
from recipe_state import RecipeState

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("asp-chef-mcp")

recipe_state = RecipeState()

_client_queues: set[asyncio.Queue[dict]] = set()

_event_loop: Optional[asyncio.AbstractEventLoop] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _event_loop
    _event_loop = asyncio.get_running_loop()
    log.info("FastAPI ready - SSE bridge is live on http://localhost:8000")
    yield


http_app = FastAPI(title="ASP Chef MCP Bridge", lifespan=lifespan)

http_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@http_app.get("/events")
async def sse_events(request: Request):
    """
    Server-Sent Events endpoint.
    The ASP Chef Svelte component connects here and receives recipe commands.
    Each command is a JSON object:  { "action": "...", ...params }
    """

    client_queue: asyncio.Queue[dict] = asyncio.Queue()
    _client_queues.add(client_queue)

    async def event_generator():
        yield "event: ping\ndata: {}\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    cmd = await asyncio.wait_for(client_queue.get(), timeout=15.0)
                    payload = json.dumps(cmd)
                    yield f"event: command\ndata: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            _client_queues.discard(client_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@http_app.post("/sync")
async def sync_recipe(request: Request):
    """
    The Svelte component POSTs the current recipe state here after every
    mutation so the MCP server always has an up-to-date snapshot.
    """
    body = await request.json()
    recipe_state.update(body.get("recipe", []), body.get("connector_index", -1))
    log.info("Recipe synced: %d operations", len(recipe_state.ingredients))
    return {"ok": True}


@http_app.post("/docs")
async def sync_docs(request: Request):
    """
    Receives the bulk operation documentation from the Svelte UI once upon connection.
    """
    body = await request.json()
    if "docs" in body:
        recipe_state.set_doc(body.get("docs"))
    log.info("Docs synced: %d operations", len(recipe_state.docs))
    return {"ok": True}


@http_app.get("/health")
async def health():
    return {"status": "ok", "operations": len(recipe_state.ingredients)}


def _send_command(cmd: dict) -> None:
    """
    Thread-safe helper. Can be called from the STDIO FastMCP thread.
    Schedules the command onto the asyncio queue that feeds SSE clients.
    """
    if _event_loop is None:
        log.warning("Event loop not ready - dropping command %s", cmd.get("action"))
        return

    async def _dispatch():
        for q in _client_queues:
            await q.put(cmd)

    asyncio.run_coroutine_threadsafe(_dispatch(), _event_loop)


mcp = FastMCP(
    "ASP Chef",
    instructions=ASP_CHEF_DOCS,
)


@mcp.tool()
def get_recipe() -> str:
    """
    Returns the current state of the ASP Chef recipe as a JSON array.
    Each element has: id (string), operation (string), options (object).
    Use this tool first to understand the current pipeline before making changes.
    """
    return json.dumps(recipe_state.ingredients, indent=2)


@mcp.tool()
def get_operation_docs(operation: str) -> str:
    """
    Returns detailed documentation and option schemas for a specific operation.
    """
    return recipe_state.get_operation_doc(operation)


@mcp.tool()
def get_operation_catalogue() -> str:
    """
    Returns a list of all available ASP Chef operations.
    Use this to discover which operations exist, then use get_operation_docs(operation)
    to get detailed information before adding them to the recipe.
    """
    operations = sorted(recipe_state.docs.keys())
    if not operations:
        return "No operations are currently loaded in the documentation dictionary."
    return "Available operations:\n- " + "\n- ".join(operations)


@mcp.tool()
def set_input(input_text: str) -> str:
    """
    Sets the contents of the ASP Chef input panel.

    Parameters
    ----------
    input_text : str
        The raw text to place into the input panel. This is the initial data
        that will be processed by the first operation in the recipe pipeline.
    """
    _send_command({"action": "set_input", "input": input_text})
    return f"✓ Queued set_input with length {len(input_text)}."


@mcp.tool()
def set_global_option(option: str, value: bool) -> str:
    """
    Set global user interface and baking options for the ASP Chef recipe panel.

    Parameters
    ----------
    option : str
        The global option to configure. Valid values:
        - "pause_baking": Pause the automatic baking/execution of the recipe (useful for performance).
        - "readonly_ingredients": Lock ingredients from being edited.
        - "show_ingredient_headers": Show/hide ingredient header bars (disables dragging when hidden).
        - "show_ingredient_details": Show/hide the details inside ingredients.
        - "show_help": Enable/disable inline help popups.
    value : bool
        True to enable/set the option, False to disable/unset.
    """
    _send_command({"action": "set_global_option", "option": option, "value": value})
    return f"✓ Queued global option '{option}' = {value}."


@mcp.tool()
def add_operation(
    operation: str,
    options: Optional[dict] = None,
    at_index: Optional[int] = None,
) -> str:
    """
    Add a new operation to the ASP Chef recipe pipeline.

    Parameters
    ----------
    operation : str
        The exact operation name (e.g. "Search Models", "Filter", "Map").
        Use get_operation_catalogue() to find valid names.
    options : dict, optional
        Operation-specific configuration. Common fields shared by all operations:
          - apply  (bool, default True)  - whether the operation is active
          - stop   (bool, default False) - pause the pipeline after this step
          - show   (bool, default True)  - show the output panel
        Check get_operation_catalogue() for operation-specific options.
    at_index : int, optional
        Insert the operation before this index (0-based).
        Omit to append before the MCP Server connector.

    Returns
    -------
    str
        Confirmation with the operation name and insertion position.
    """
    opts = options or {}
    
    # Enforce standard defaults natively in python 
    opts.setdefault("apply", True)
    opts.setdefault("show", True)
    opts.setdefault("stop", False)

    cmd: dict[str, Any] = {
        "action": "add_operation",
        "operation": operation,
        "options": opts,
    }
    if at_index is not None:
        cmd["at_index"] = at_index

    _send_command(cmd)
    pos = at_index if at_index is not None else "before MCP connector"
    return f"✓ Queued add_operation '{operation}' at position {pos}."


@mcp.tool()
def remove_operation(at_index: int) -> str:
    """
    Remove the operation at the given index from the recipe.

    Parameters
    ----------
    at_index : int
        0-based index of the operation to remove.
        Use get_recipe() to see current indices.
    """
    _send_command({"action": "remove_operation", "at_index": at_index})
    return f"✓ Queued remove_operation at index {at_index}."


@mcp.tool()
def remove_all_operations() -> str:
    """
    Remove ALL operations from the recipe, resetting it to an empty pipeline.
    Use with caution - this cannot be undone through the MCP server.
    """
    _send_command({"action": "remove_all_operations"})
    return "✓ Queued remove_all_operations."


@mcp.tool()
def edit_operation(op_id: str, at_index: int, options: dict) -> str:
    """
    Update the options of an existing operation without changing its type or position.

    Parameters
    ----------
    op_id : str
        The unique UUID of the operation (from get_recipe()).
    at_index : int
        The current index of the operation (used as a fast-path hint).
    options : dict
        The complete new options object. Include all fields, not just changed ones.
    """
    _send_command(
        {
            "action": "edit_operation",
            "op_id": op_id,
            "at_index": at_index,
            "options": options,
        }
    )
    return f"✓ Queued edit_operation for id={op_id}."


@mcp.tool()
def swap_operations(index_1: int, index_2: int) -> str:
    """
    Swap the positions of two operations in the recipe.

    Parameters
    ----------
    index_1 : int
        0-based index of the first operation.
    index_2 : int
        0-based index of the second operation.
    """
    _send_command({"action": "swap_operations", "index_1": index_1, "index_2": index_2})
    return f"✓ Queued swap_operations {index_1} ↔ {index_2}."


@mcp.tool()
def duplicate_operation(at_index: int) -> str:
    """
    Duplicate the operation at the given index and insert the copy immediately after it.

    Parameters
    ----------
    at_index : int
        0-based index of the operation to duplicate.
    """
    _send_command({"action": "duplicate_operation", "at_index": at_index})
    return f"✓ Queued duplicate_operation at index {at_index}."


@mcp.tool()
def remove_operations(at_index: int, how_many: int = 0) -> str:
    """
    Remove a contiguous slice of operations from the recipe.

    Parameters
    ----------
    at_index : int
        Start index of the slice (inclusive).
    how_many : int
        Number of operations to remove. 0 means remove everything from at_index onward.
    """
    _send_command(
        {"action": "remove_operations", "at_index": at_index, "how_many": how_many}
    )
    return f"✓ Queued remove_operations from index {at_index} (×{how_many or 'all'})."


@mcp.tool()
def toggle_apply(at_index: int) -> str:
    """
    Toggle whether the operation at the given index is active (applied) in the pipeline.
    Inactive operations are skipped during execution.

    Parameters
    ----------
    at_index : int
        0-based index of the operation.
    """
    _send_command({"action": "toggle_apply_operation", "at_index": at_index})
    return f"✓ Queued toggle_apply at index {at_index}."


@mcp.tool()
def toggle_stop(at_index: int) -> str:
    """
    Toggle the 'stop' flag on the operation at the given index.
    When enabled, the pipeline pauses after executing this operation
    (useful for debugging intermediate results).

    Parameters
    ----------
    at_index : int
        0-based index of the operation.
    """
    _send_command({"action": "toggle_stop_at_operation", "at_index": at_index})
    return f"✓ Queued toggle_stop at index {at_index}."


@mcp.tool()
def toggle_show(at_index: int) -> str:
    """
    Toggle whether the output of the operation at the given index is shown in the UI.

    Parameters
    ----------
    at_index : int
        0-based index of the operation.
    """
    _send_command({"action": "toggle_show_operation", "at_index": at_index})
    return f"✓ Queued toggle_show at index {at_index}."


@mcp.tool()
def fix_operation(op_id: str, at_index: int, operation: str) -> str:
    """
    Change the type of an existing operation without touching its options or position.
    Useful for replacing a placeholder with the correct operation name.

    Parameters
    ----------
    op_id : str
        UUID of the operation to change (from get_recipe()).
    at_index : int
        Current 0-based index (fast-path hint).
    operation : str
        The new operation name.
    """
    _send_command(
        {
            "action": "fix_operation",
            "op_id": op_id,
            "at_index": at_index,
            "operation": operation,
        }
    )
    return f"✓ Queued fix_operation id={op_id} → '{operation}'."


@mcp.tool()
def process_recipe(input_text: str, encode: bool = False) -> str:
    """
    Process the recipe with the given input. This executes the entire pipeline
    on the client side using the provided input string.

    Parameters
    ----------
    input_text : str
        The raw string input to feed into the recipe pipeline.
    encode : bool, optional
        If True, the input is Base64 encoded and wrapped in an ASP fact.
        If False (default), it is treated as one or more ASP models separated by '§'.
    """
    _send_command({
        "action": "process_recipe",
        "input": input_text,
        "encode": encode
    })
    return f"✓ Queued process_recipe with input length {len(input_text)} (encoded: {encode})."


@mcp.tool()
def build_asp_pipeline(description: str) -> str:
    """
    High-level tool: given a plain-language description of what the ASP pipeline
    should do, suggest a sequence of add_operation calls to build it.

    This tool does NOT modify the recipe - it returns a plan as text so you can
    review it before calling add_operation for each step.

    Parameters
    ----------
    description : str
        Natural-language description of the desired pipeline behaviour.
        Example: "Parse a graph from input, find all 3-colorings, and display them."

    Returns
    -------
    str
        A step-by-step plan with recommended operations and options.
    """
    return (
        f"Pipeline planning request: '{description}'\n\n"
        "To build this pipeline, consider the following steps:\n"
        "1. Call get_operation_catalogue() to browse available operations.\n"
        "2. Call get_operation_docs(operation) to understand specific operations.\n"
        "3. Call get_recipe() to see the current state.\n"
        "4. Use add_operation() for each step in the desired order.\n\n"
        "Refer to the ASP Chef documentation in the system prompt for operation "
        "semantics and option schemas."
    )


def _run_http_server():
    """Runs the FastAPI/uvicorn server on port 8000 in a daemon thread."""
    config = uvicorn.Config(
        http_app,
        host="127.0.0.1",
        port=8000,
        log_level="warning",
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    server.run()


def main():
    """Entry point for Claude Desktop (STDIO transport)."""
    t = threading.Thread(target=_run_http_server, daemon=True, name="http-bridge")
    t.start()
    log.info("HTTP/SSE bridge starting on http://127.0.0.1:8000 …")

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

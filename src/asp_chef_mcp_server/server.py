"""
ASP Chef MCP Server
===================
Dual-transport server:
  • STDIO  → Claude Desktop (MCP protocol via FastMCP)
  • HTTP   → ASP Chef browser UI (SSE commands + /sync endpoint via FastAPI)
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
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

_pending_requests: dict[str, tuple[threading.Event, dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _event_loop
    _event_loop = asyncio.get_running_loop()
    log.info("FastAPI ready - SSE bridge is live on http://127.0.0.1:8000")
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
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@http_app.post("/sync")
async def sync_recipe(request: Request):
    body = await request.json()
    errors = body.get("errors", [])
    
    recipe_state.update(body) 
    
    req_id = body.get("request_id")
    if req_id and req_id in _pending_requests:
        evt, result_box = _pending_requests[req_id]
        result_box["errors"] = errors
        evt.set()

    return {"ok": True}


@http_app.post("/docs")
async def sync_docs(request: Request):
    body = await request.json()
    if "docs" in body:
        recipe_state.set_doc(body.get("docs"))
    log.info("Docs synced: %d operations loaded.", len(recipe_state.docs))
    return {"ok": True}


@http_app.get("/health")
async def health():
    return {"status": "ok", "operations": len(recipe_state.ingredients)}


def _send_command(cmd: dict) -> str | None:
    """Invia il comando via SSE e attende l'esito. Ritorna None se successo, altrimenti stringa di errore."""
    if _event_loop is None:
        log.warning("Event loop not ready - dropping command")
        return "System error: Event loop not ready"

    req_id = str(uuid.uuid4())
    cmd["request_id"] = req_id

    evt = threading.Event()
    result_box = {}
    _pending_requests[req_id] = (evt, result_box)

    async def _dispatch():
        for q in _client_queues:
            await q.put(cmd)

    asyncio.run_coroutine_threadsafe(_dispatch(), _event_loop)

    success = evt.wait(timeout=3.0)
    _pending_requests.pop(req_id, None)

    if not success:
        return "Timeout: Action sent, but did not receive confirmation from browser. Recipe might still be processing."

    # Controlla se la pipeline ha generato errori dopo il comando
    errors = result_box.get("errors", [])
    if errors:
        err_msg = next((e for e in errors if e), None)
        if err_msg:
            return f"Pipeline compilation failed with error: {err_msg}"

    return None

mcp = FastMCP("ASP Chef", instructions=ASP_CHEF_DOCS)


@mcp.tool()
def get_recipe() -> str:
    """Get the current state of the ASP Chef recipe pipeline (list of active ingredients)."""
    return json.dumps(recipe_state.raw_state, indent=2)


@mcp.tool()
def get_operation_docs(operation: str) -> str:
    """Get the detailed documentation and expected options schema for a specific operation."""
    return recipe_state.get_operation_doc(operation)


@mcp.tool()
def search_operations(query: str) -> str:
    """Search for operations matching a keyword in their name or documentation."""
    query = query.lower()
    results = []
    for op, doc in recipe_state.docs.items():
        if query in op.lower() or query in doc.lower():
            results.append(op)

    if not results:
        return f"No operations found matching '{query}'."
    return "Found operations:\n- " + "\n- ".join(results)


@mcp.tool()
def get_operation_categories() -> str:
    """Explore available tools grouped alphabetically to find the right operation."""
    operations = sorted(recipe_state.docs.keys())
    if not operations:
        return "No operations are currently loaded."

    groups: dict[str, list[str]] = {}
    for op in operations:
        letter = op[0].upper() if op else "#"
        if not letter.isalpha():
            letter = "#"
        groups.setdefault(letter, []).append(op)

    result = "Available operations grouped alphabetically:\n\n"
    for letter, ops in groups.items():
        result += f"[{letter}]\n- " + "\n- ".join(ops) + "\n\n"
    return result.strip()


@mcp.tool()
def set_input(input_text: str, encode: bool = False) -> str:
    """Sets the input text for the pipeline, optionally encoding it first."""
    err = _send_command({"action": "set_input", "input": input_text, "encode": encode})
    if err:
        return f"❌ {err}"
    return f"✓ set_input applied with length {len(input_text)} (encoded: {encode})."


@mcp.tool()
def set_global_option(option: str, value: bool) -> str:
    err = _send_command(
        {"action": "set_global_option", "option": option, "value": value}
    )
    if err:
        return f"❌ {err}"
    return f"✓ Global option '{option}' = {value}."


@mcp.tool()
def add_operation(
    operation: str, options: Optional[dict] = None, at_index: Optional[int] = None
) -> str:
    opts = options or {}
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

    err = _send_command(cmd)
    if err:
        return f"❌ Action executed, but {err}"
    pos = at_index if at_index is not None else "before MCP connector"
    return f"✓ added operation '{operation}' at position {pos}."


@mcp.tool()
def remove_operation(at_index: int) -> str:
    err = _send_command({"action": "remove_operation", "at_index": at_index})
    if err:
        return f"❌ {err}"
    return f"✓ remove_operation at index {at_index}."


@mcp.tool()
def remove_all_operations() -> str:
    err = _send_command({"action": "remove_all_operations"})
    if err:
        return f"❌ {err}"
    return "✓ remove_all_operations applied."


@mcp.tool()
def edit_operation(op_id: str, at_index: int, options: dict) -> str:
    err = _send_command(
        {
            "action": "edit_operation",
            "op_id": op_id,
            "at_index": at_index,
            "options": options,
        }
    )
    if err:
        return f"❌ Action executed, but {err}"
    return f"✓ edit_operation applied for id={op_id}."


@mcp.tool()
def swap_operations(index_1: int, index_2: int) -> str:
    err = _send_command(
        {"action": "swap_operations", "index_1": index_1, "index_2": index_2}
    )
    if err:
        return f"❌ Action executed, but {err}"
    return f"✓ swap_operations {index_1} ↔ {index_2}."


@mcp.tool()
def duplicate_operation(at_index: int) -> str:
    err = _send_command({"action": "duplicate_operation", "at_index": at_index})
    if err:
        return f"❌ Action executed, but {err}"
    return f"✓ duplicate_operation at index {at_index}."


@mcp.tool()
def remove_operations(at_index: int, how_many: int = 0) -> str:
    err = _send_command(
        {"action": "remove_operations", "at_index": at_index, "how_many": how_many}
    )
    if err:
        return f"❌ {err}"
    return f"✓ remove_operations from index {at_index} (×{how_many or 'all'})."


@mcp.tool()
def toggle_apply(at_index: int) -> str:
    err = _send_command({"action": "toggle_apply_operation", "at_index": at_index})
    if err:
        return f"❌ Action executed, but {err}"
    return f"✓ toggle_apply at index {at_index}."


@mcp.tool()
def toggle_stop(at_index: int) -> str:
    err = _send_command({"action": "toggle_stop_at_operation", "at_index": at_index})
    if err:
        return f"❌ {err}"
    return f"✓ toggle_stop at index {at_index}."


@mcp.tool()
def toggle_show(at_index: int) -> str:
    err = _send_command({"action": "toggle_show_operation", "at_index": at_index})
    if err:
        return f"❌ {err}"
    return f"✓ toggle_show at index {at_index}."


@mcp.tool()
def fix_operation(op_id: str, at_index: int, operation: str) -> str:
    err = _send_command(
        {
            "action": "fix_operation",
            "op_id": op_id,
            "at_index": at_index,
            "operation": operation,
        }
    )
    if err:
        return f"❌ Action executed, but {err}"
    return f"✓ fix_operation id={op_id} → '{operation}'."


def _run_http_server():

    config = uvicorn.Config(
        http_app, host="127.0.0.1", port=8000, log_level="warning", loop="asyncio"
    )
    server = uvicorn.Server(config)
    server.run()


def main():
    t = threading.Thread(target=_run_http_server, daemon=True, name="http-bridge")
    t.start()
    log.info("HTTP/SSE bridge starting on http://127.0.0.1:8000 …")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

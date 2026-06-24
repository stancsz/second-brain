#!/usr/bin/env python3
"""second-brain MCP server — stdlib-only, zero-dependency.

Exposes the SecondBrain knowledge graph over the Model Context Protocol so any
MCP client (Claude Desktop, Cursor, Continue, custom hosts) can read and write
your brain — the same `~/.secondbrain/brain.db` the CLI and the Claude Code
skill use. No SDK, no `pip install`: this implements MCP's stdio transport
(newline-delimited JSON-RPC 2.0) directly on the Python standard library, in
keeping with the project's zero-deps core invariant.

Run it directly:
    python3 scripts/brain_mcp.py

Or register it with an MCP client (Claude Desktop config example):
    {
      "mcpServers": {
        "second-brain": {
          "command": "python3",
          "args": ["/abs/path/to/second-brain/scripts/brain_mcp.py"]
        }
      }
    }

The protocol channel is stdout — nothing but framed JSON-RPC may go there.
All diagnostics go to stderr (ASCII-safe, per the repo's encoding discipline).
"""
import json
import sys
from pathlib import Path

# brain.py lives next to this file; import it without assuming CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import SecondBrain  # noqa: E402

# stdout carries JSON-RPC; force UTF-8 but never print anything else there.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "second-brain"
SERVER_VERSION = "3.0"


def _log(msg: str) -> None:
    """Diagnostics to stderr only. ASCII to stay safe across cp1252 readers."""
    sys.stderr.write(f"[second-brain-mcp] {msg}\n")
    sys.stderr.flush()


# --- Tool definitions ------------------------------------------------------
# Each entry: name -> (json-schema, handler(brain, args) -> str).

TOOLS = [
    {
        "name": "brain_add",
        "description": "Save a new Concept (note) to the brain. Content may "
                       "contain [[wikilinks]] which auto-resolve into relations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Concept title (unique handle)."},
                "content": {"type": "string", "description": "Body text; supports [[wikilinks]]."},
                "collection": {"type": "string", "description": "Optional collection name."},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags."},
                "sources": {"type": "array", "items": {"type": "string"}, "description": "Optional source URLs/refs."},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "brain_search",
        "description": "Full-text search the brain. Returns matching Concepts "
                       "(title, snippet, id).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "collection": {"type": "string"},
                "tag": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "brain_show",
        "description": "Show one Concept in full by id or exact title, including "
                       "its relations.",
        "inputSchema": {
            "type": "object",
            "properties": {"ident": {"type": "string", "description": "Concept id or title."}},
            "required": ["ident"],
        },
    },
    {
        "name": "brain_list",
        "description": "List Concepts, optionally filtered by collection or tag.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "collection": {"type": "string"},
                "tag": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
                "sort": {"type": "string", "enum": ["updated", "created", "title"], "default": "updated"},
            },
        },
    },
    {
        "name": "brain_related",
        "description": "List Concepts related to a given Concept id (typed "
                       "relations + wikilinks).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["id"],
        },
    },
    {
        "name": "brain_recall_subject",
        "description": "Recall every memory about one subject (a person/topic), "
                       "e.g. the persona sub-graph. Accepts a path (/people/rox.md) "
                       "or a display name (rox).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["subject"],
        },
    },
    {
        "name": "brain_recall_as_of",
        "description": "Point-in-time recall: return only facts whose bi-temporal "
                       "validity window contains the given ISO date.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "as_of": {"type": "string", "description": "ISO date, e.g. 2023-06-01."},
                "query": {"type": "string", "description": "Optional FTS query to narrow."},
                "collection": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["as_of"],
        },
    },
    {
        "name": "brain_stats",
        "description": "Brain health: concept/relation counts, top tags, collections.",
        "inputSchema": {
            "type": "object",
            "properties": {"collection": {"type": "string"}},
        },
    },
]


def _h_add(b, a):
    tags = a.get("tags") or []
    dr = b.add(a["title"], a["content"], a.get("collection"), tags, a.get("sources") or [])
    links = b.related(dr["id"], source="wikilink")
    res = {"id": dr["id"], "title": dr["title"],
           "linked": [x["title"] for x in links]}
    return json.dumps(res, ensure_ascii=False, default=str)


def _h_search(b, a):
    res = b.search(a["query"], a.get("collection"), a.get("tag"), a.get("limit", 10))
    return json.dumps(res, ensure_ascii=False, default=str)


def _h_show(b, a):
    ident = a["ident"]
    matches = [b.get(ident)] if b.get(ident) else b.get_by_title(ident)
    matches = [m for m in matches if m]
    if not matches:
        return json.dumps({"error": f"No live concept matches '{ident}'."}, ensure_ascii=False)
    if len(matches) > 1:
        return json.dumps({"ambiguous": matches}, ensure_ascii=False, default=str)
    dd = matches[0]
    dd = dict(dd)
    dd["relations"] = b.related(matches[0]["id"])
    return json.dumps(dd, ensure_ascii=False, default=str)


def _h_list(b, a):
    res = b.list(a.get("collection"), a.get("tag"), a.get("limit", 20), 0, a.get("sort", "updated"))
    return json.dumps(res, ensure_ascii=False, default=str)


def _h_related(b, a):
    res = b.related(a["id"], a.get("limit", 20))
    return json.dumps(res, ensure_ascii=False, default=str)


def _h_recall_subject(b, a):
    sub_in = a["subject"]
    if not sub_in.startswith("/"):
        match = b.con.execute(
            "SELECT sb_id FROM subjects WHERE slug = ? OR display_name = ?",
            (sub_in.lower(), sub_in),
        ).fetchone()
        if match:
            sub_in = match["sb_id"]
    res = b.subject_subgraph(sub_in)[: a.get("limit", 50)]
    return json.dumps({"subject": sub_in, "concepts": res}, ensure_ascii=False, default=str)


def _h_recall_as_of(b, a):
    res = b.recall_as_of(a["as_of"], query=a.get("query"),
                         collection=a.get("collection"), limit=a.get("limit", 50))
    return json.dumps({"as_of": a["as_of"], "concepts": res}, ensure_ascii=False, default=str)


def _h_stats(b, a):
    return json.dumps(b.stats(a.get("collection")), ensure_ascii=False, default=str)


HANDLERS = {
    "brain_add": _h_add,
    "brain_search": _h_search,
    "brain_show": _h_show,
    "brain_list": _h_list,
    "brain_related": _h_related,
    "brain_recall_subject": _h_recall_subject,
    "brain_recall_as_of": _h_recall_as_of,
    "brain_stats": _h_stats,
}


# --- JSON-RPC plumbing -----------------------------------------------------

def _result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _handle(req, brain_holder):
    """Return a response dict, or None for notifications (no reply)."""
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        return _result(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })

    if method == "notifications/initialized":
        return None  # notification — no response

    if method == "ping":
        return _result(req_id, {})

    if method == "tools/list":
        return _result(req_id, {"tools": TOOLS})

    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        handler = HANDLERS.get(name)
        if handler is None:
            return _error(req_id, -32602, f"Unknown tool: {name}")
        try:
            if brain_holder["brain"] is None:
                brain_holder["brain"] = SecondBrain()
            text = handler(brain_holder["brain"], args)
            return _result(req_id, {"content": [{"type": "text", "text": text}]})
        except Exception as ex:  # surface tool errors to the client, don't crash
            _log(f"tool {name} failed: {ex}")
            return _result(req_id, {
                "content": [{"type": "text", "text": f"Error: {ex}"}],
                "isError": True,
            })

    if req_id is None:
        return None  # unknown notification — ignore
    return _error(req_id, -32601, f"Method not found: {method}")


def main():
    _log("starting (stdio transport)")
    brain_holder = {"brain": None}
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as ex:
            _log(f"bad JSON: {ex}")
            sys.stdout.write(json.dumps(_error(None, -32700, "Parse error")) + "\n")
            sys.stdout.flush()
            continue
        resp = _handle(req, brain_holder)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    if brain_holder["brain"] is not None:
        brain_holder["brain"].close()
    _log("stdin closed, exiting")


if __name__ == "__main__":
    main()

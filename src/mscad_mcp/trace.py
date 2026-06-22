"""Workflow tracing for the MCP server.

Captures every tool call — name, arguments, result summary, status, and
duration — to a per-session JSONL file. The goal is to build a corpus of
real survey/CAD workflows ("which operations chain, in what order, with what
defaults") while the licensed software is still available, so an open-source
clone can later be specified and validated against it.

Design notes
------------
- Zero behavioural impact: tracing only observes; it never alters a tool's
  return value, and any failure inside the tracer is swallowed (a broken
  logger must never break a CAD operation).
- Two entry points:
    * install_tracing(mcp, ...) — wraps FastMCP's @mcp.tool() decorator so
      every registered tool is traced. Used by the in-process (sync) server.
    * log_call(...) — log one call directly. Used at a single chokepoint
      (e.g. an HTTP bridge function) when decorator-wrapping isn't wanted.
- Signature preservation: the wrapper copies __signature__ and annotations so
  FastMCP/Pydantic still builds the correct JSON schema for each tool.

Environment
-----------
- {PREFIX}_TRACE      "0"/"off"/"false" disables tracing (default: enabled).
- {PREFIX}_TRACE_DIR  directory for JSONL files (default: <project>/traces).
where {PREFIX} is passed to install_tracing/configure (e.g. "MSCAD_MCP").
"""

from __future__ import annotations

import os
import json
import time
import uuid
import inspect
import functools
import threading
import datetime as _dt

_LOCK = threading.Lock()
_STATE: dict = {
    "enabled": False,
    "app": "unknown",
    "path": None,
    "session": None,
    "seq": 0,
}

# Cap large string fields in the *result* summary. Inputs (params) are kept
# whole — they are the high-value part. Results are only summarised because
# the authoritative golden output is the saved native file / export, not the
# trace. Big blobs (generated LISP, etc.) would just bloat the log.
_MAX_RESULT_STR = 4000


def _truthy_disabled(val: str | None) -> bool:
    return (val or "").strip().lower() in {"0", "off", "false", "no"}


def configure(app_name: str, env_prefix: str, default_dir: str) -> None:
    """Initialise tracing state and write a session-start record.

    Safe to call once at server startup. If tracing is disabled via env, this
    is a no-op apart from setting enabled=False.
    """
    enabled = not _truthy_disabled(os.environ.get(f"{env_prefix}_TRACE"))
    _STATE["enabled"] = enabled
    _STATE["app"] = app_name
    if not enabled:
        return

    trace_dir = os.environ.get(f"{env_prefix}_TRACE_DIR") or default_dir
    try:
        os.makedirs(trace_dir, exist_ok=True)
    except Exception:
        _STATE["enabled"] = False
        return

    session = _dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    _STATE["session"] = session
    _STATE["path"] = os.path.join(trace_dir, f"{app_name}-{session}.jsonl")
    _STATE["seq"] = 0

    _append({
        "kind": "session_start",
        "app": app_name,
        "pid": os.getpid(),
        "cwd": os.getcwd(),
    })


def _append(record: dict) -> None:
    """Append one record as a JSONL line. Never raises."""
    if not _STATE["enabled"] or not _STATE["path"]:
        return
    try:
        with _LOCK:
            _STATE["seq"] += 1
            record = {
                "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "session": _STATE["session"],
                "app": _STATE["app"],
                "seq": _STATE["seq"],
                **record,
            }
            with open(_STATE["path"], "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")
    except Exception:
        # A tracing failure must never propagate into a CAD operation.
        pass


def _summarise(value):
    """Truncate long strings and cap container sizes for the result summary."""
    if isinstance(value, str):
        if len(value) > _MAX_RESULT_STR:
            return value[:_MAX_RESULT_STR] + f"...<+{len(value) - _MAX_RESULT_STR} chars>"
        return value
    if isinstance(value, dict):
        return {k: _summarise(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        if len(value) > 200:
            return [_summarise(v) for v in value[:200]] + [f"...<+{len(value) - 200} items>"]
        return [_summarise(v) for v in value]
    return value


def _infer_status(result) -> str:
    if isinstance(result, dict):
        s = result.get("status")
        if isinstance(s, str):
            return s
        if "error" in result and result["error"]:
            return "error"
    return "ok"


def log_call(tool: str, params: dict, result=None, *,
             duration_ms: float | None = None, error: str | None = None) -> None:
    """Log a single tool/bridge call. Used directly at HTTP-bridge chokepoints."""
    _append({
        "kind": "call",
        "tool": tool,
        "params": _summarise(params or {}),
        "result": None if error else _summarise(result),
        "status": "error" if error else _infer_status(result),
        "duration_ms": round(duration_ms, 1) if duration_ms is not None else None,
        "error": error,
    })


def _bind_args(fn, args, kwargs) -> dict:
    try:
        bound = inspect.signature(fn).bind(*args, **kwargs)
        bound.apply_defaults()
        return dict(bound.arguments)
    except Exception:
        return {"_args": _summarise(list(args)), "_kwargs": _summarise(dict(kwargs))}


def _wrap_fn(fn):
    """Return a logging wrapper that preserves fn's signature for schema gen."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        params = _bind_args(fn, args, kwargs)
        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            log_call(fn.__name__, params, None,
                     duration_ms=(time.perf_counter() - t0) * 1000, error=repr(e))
            raise
        log_call(fn.__name__, params, result,
                 duration_ms=(time.perf_counter() - t0) * 1000)
        return result

    # Critical: FastMCP/Pydantic introspect the signature + annotations to
    # build each tool's JSON schema. functools.wraps copies annotations and
    # __wrapped__; we set __signature__ explicitly to be safe.
    try:
        wrapper.__signature__ = inspect.signature(fn)
    except (ValueError, TypeError):
        pass
    return wrapper


def install_tracing(mcp, app_name: str, env_prefix: str, default_dir: str) -> None:
    """Patch mcp.tool() so every subsequently-registered tool is traced.

    Call this immediately after creating the FastMCP instance and BEFORE the
    tool modules are imported, so the patched decorator is in effect when each
    @mcp.tool() runs.
    """
    configure(app_name, env_prefix, default_dir)
    if not _STATE["enabled"]:
        return

    original_tool = mcp.tool

    def traced_tool(*d_args, **d_kwargs):
        real_decorator = original_tool(*d_args, **d_kwargs)

        def decorator(fn):
            return real_decorator(_wrap_fn(fn))

        return decorator

    mcp.tool = traced_tool

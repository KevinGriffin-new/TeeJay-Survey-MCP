"""MCP server for MicroSurvey CAD 2024."""

import logging
import os
from mcp.server.fastmcp import FastMCP

# Configure logging to file (stdout is the MCP transport)
log_path = os.path.join(os.path.dirname(__file__), "..", "..", "mscad-mcp.log")
logging.basicConfig(
    filename=os.path.abspath(log_path),
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

mcp = FastMCP(
    "MicroSurvey CAD 2024",
    instructions="Control MicroSurvey CAD 2024 — draw entities, manage layers, open/save drawings, run CAD commands, COGO calculations, survey point management, traverse operations, surface/TIN modeling, and coordinate transformations.",
)

# Workflow tracing — wraps mcp.tool() so every tool below is logged to
# traces/*.jsonl. MUST be installed before the tool-module imports so the
# patched decorator is in effect when each @mcp.tool() runs.
# Disable with MSCAD_MCP_TRACE=0; redirect with MSCAD_MCP_TRACE_DIR.
from mscad_mcp import trace  # noqa: E402

trace.install_tracing(
    mcp,
    app_name="MicroSurveyCAD",
    env_prefix="MSCAD_MCP",
    default_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "traces")),
)

# Import tool modules to register them with the server
from mscad_mcp.tools import app  # noqa: F401, E402
from mscad_mcp.tools import drawing  # noqa: F401, E402
from mscad_mcp.tools import layers  # noqa: F401, E402
from mscad_mcp.tools import entities  # noqa: F401, E402
from mscad_mcp.tools import query  # noqa: F401, E402
from mscad_mcp.tools import modify  # noqa: F401, E402
from mscad_mcp.tools import view  # noqa: F401, E402
from mscad_mcp.tools import cogo  # noqa: F401, E402
from mscad_mcp.tools import survey  # noqa: F401, E402
from mscad_mcp.tools import traverse  # noqa: F401, E402
from mscad_mcp.tools import surface  # noqa: F401, E402
from mscad_mcp.tools import transform  # noqa: F401, E402
from mscad_mcp.tools import msannotate  # noqa: F401, E402
from mscad_mcp.tools import settings  # noqa: F401, E402
from mscad_mcp.tools import automap  # noqa: F401, E402
from mscad_mcp.tools import template  # noqa: F401, E402


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

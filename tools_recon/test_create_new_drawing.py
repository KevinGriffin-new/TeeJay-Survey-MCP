"""Live end-to-end smoke test for the create_new_drawing MCP tool.

Calls the tool function directly against the running MicroSurvey CAD and prints
the staged result. Creates a throwaway job in the Jobs folder.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mscad_mcp.tools import drawing  # noqa: E402


def main():
    result = drawing.create_new_drawing(
        name="_MCPTEST",
        distance_units="us_feet",
        direction="bearings",
        scale_factor=500,
        job_description="MCP smoke test",
    )
    print(result)


if __name__ == "__main__":
    main()

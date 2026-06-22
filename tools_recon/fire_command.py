"""Fire a single MSCAD command via COM SendCommand, for dialog recon.

Connects to the running Icad.exe and sends the command. Commands that open a
modal dialog will block here until the dialog closes, so run this in the
background and probe the dialog from a separate process.

Usage:
  python fire_command.py "_project_manager "
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mscad_mcp import connection


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "_project_manager "
    app = connection.connect()
    try:
        doc = app.ActiveDocument
        doc.SendCommand(cmd)
        print(f"sent: {cmd!r}")
    except Exception as e:
        print(f"error: {e}")


if __name__ == "__main__":
    main()

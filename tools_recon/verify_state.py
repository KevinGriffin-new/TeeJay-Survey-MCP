import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mscad_mcp import connection

app = connection.connect()
doc = app.ActiveDocument
print("ActiveDocument.Name:", doc.Name)
try:
    print("FullName:", doc.FullName)
except Exception as e:
    print("FullName err:", e)
# Drawing scale-ish system variables, if accessible.
for var in ("LTSCALE", "DIMSCALE", "INSUNITS", "AUNITS"):
    try:
        print(var, "=", doc.GetVariable(var))
    except Exception as e:
        print(var, "err:", e)

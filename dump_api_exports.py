# dump_api_exports.py
import traceback
import json
import sys
import rvc_python.api as api_mod

output = {
    "dir": dir(api_mod),
    "app_present": False,
    "import_app_error": None,
}

try:
    from rvc_python.api import app  # attempt import
    output["app_present"] = True
    output["app_repr"] = repr(app)
except Exception as e:
    output["import_app_error"] = str(e)
    output["import_app_traceback"] = traceback.format_exc()

# Write to stdout (captured in RunPod logs) and to a file for persistence
print("INTROSPECTION RESULT:", json.dumps(output, indent=2))
with open("/home/appuser/app/rvc_api_introspection.json", "w") as f:
    json.dump(output, f, indent=2)

# Keep the container alive briefly so you can fetch logs or the file
import time; time.sleep(30)
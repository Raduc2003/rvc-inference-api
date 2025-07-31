import runpod.serverless
from fastapi.testclient import TestClient
from rvc_python.api import app  # Import the FastAPI app inside rvc-python

client = TestClient(app)

def handler(job):
    """
    job["input"] = {
      "api": {"method":"GET"|"POST", "endpoint":"/models" or "/convert"},
      "payload": {...}
    }
    """
    api      = job["input"]["api"]
    payload  = job["input"].get("payload", {})

    # Dispatch internally to the rvc_python FastAPI app
    if api["method"].upper() == "GET":
        resp = client.get(api["endpoint"], params=payload)
    else:
        resp = client.post(api["endpoint"], json=payload)

    # Return parsed JSON (or raw bytes for audio)
    try:
        return resp.json()
    except ValueError:
        return resp.content

# Start the serverless worker with our handler
runpod.serverless.start({"handler": handler})

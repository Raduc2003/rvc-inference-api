# runpod.py
import runpod.serverless
from fastapi.testclient import TestClient
from main import app  # your FastAPI app

client = TestClient(app)

def handler(job):
    """
    job: { "id": "...", "input": { "api": { "method": "...", "endpoint": "..." }, "payload": {...} } }
    """
    method   = job["input"]["api"]["method"]
    endpoint = job["input"]["api"]["endpoint"]
    payload  = job["input"].get("payload", {})

    # Dispatch internally to FastAPI
    if method.upper() == "GET":
        resp = client.get(endpoint, params=payload)
    else:
        resp = client.post(endpoint, json=payload)

    # Return the JSON or raw content depending on your route
    try:
        return resp.json()
    except ValueError:
        return resp.content

# Register the handler with RunPod Serverless
runpod.serverless.start({"handler": handler})

# runpod_handler.py
import runpod.serverless
from fastapi.testclient import TestClient
from rvc_python.api import create_app
import os
import base64

def list_models_directly():
    model_dir = os.getenv("RVC_MODELDIR", "/runpod-volume/models")
    if not os.path.isdir(model_dir):
        return {"models": []}
    names = []
    for entry in os.listdir(model_dir):
        path = os.path.join(model_dir, entry)
        if os.path.isdir(path):
            names.append(entry)
        elif entry.endswith(".pth"):
            names.append(os.path.splitext(entry)[0])
    return {"models": names}

def handler(job):
    inp = job.get("input", {})
    api = inp.get("api", {})
    method = api.get("method", "GET").upper()
    endpoint = api.get("endpoint", "/models")
    payload = inp.get("payload", {})

    # Short-circuit GET /models
    if endpoint == "/models" and method == "GET":
        return list_models_directly()

    # Build and enter the app context so startup runs
    app = create_app()
    with TestClient(app) as client:
        # 1. Set models directory (required)
        models_dir = os.getenv("RVC_MODELDIR", "/runpod-volume/models")
        client.post("/set_models_dir", json={"models_dir": models_dir})

        # If the job wants to load a model (or ensure it's loaded before convert), do it here
        model_name = payload.get("model_name") or payload.get("model")  # accept either key
        if model_name:
            client.post(f"/models/{model_name}", json={})

        # Dispatch based on endpoint
        if method == "GET":
            resp = client.get(endpoint, params=payload)
        else:
            if endpoint == "/convert":
                # Expect raw base64 audio_data in payload
                audio_data = payload.get("audio_data")
                if not audio_data:
                    return {"error": "Missing audio_data in payload for /convert"}
                resp = client.post("/convert", json={"audio_data": audio_data})
            else:
                resp = client.post(endpoint, json=payload)

        try:
            return resp.json()
        except ValueError:
            return resp.content

runpod.serverless.start({"handler": handler})

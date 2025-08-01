import runpod.serverless
from fastapi.testclient import TestClient
from rvc_python.api import create_app
import os
import base64
import io

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

    # Otherwise use rvc-python internal API
    app = create_app()
    with TestClient(app) as client:
        # Ensure the models directory is set so internal state can initialize properly
        models_dir = os.getenv("RVC_MODELDIR", "/runpod-volume/models")
        client.post("/set_models_dir", json={"models_dir": models_dir})

        if method == "GET":
            resp = client.get(endpoint, params=payload)
        else:
            if endpoint.startswith("/convert"):
                # Prefer raw base64 audio_data if provided
                audio_data = payload.get("audio_data")
                if audio_data:
                    # send JSON with audio_data
                    resp = client.post("/convert", json={"audio_data": audio_data})
                else:
                    # fallback to file_b64 (data URI), convert to raw base64
                    file_b64 = payload.get("file_b64")
                    if file_b64:
                        if file_b64.startswith("data:"):
                            _, encoded = file_b64.split(",", 1)
                        else:
                            encoded = file_b64
                        resp = client.post("/convert", json={"audio_data": encoded})
                    else:
                        # Neither provided: forward raw payload in case other shapes are supported
                        resp = client.post(endpoint, json=payload)
            else:
                resp = client.post(endpoint, json=payload)

        try:
            return resp.json()
        except ValueError:
            return resp.content

runpod.serverless.start({"handler": handler})

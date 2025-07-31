# runpod_handler.py
import runpod.serverless
from fastapi.testclient import TestClient
from rvc_python.api import create_app  # use the factory
import os
import base64
import io
import soundfile as sf

# Instantiate the FastAPI app using the provided factory
app = create_app()
client = TestClient(app)

def handler(job):
    inp = job.get("input", {})
    api = inp.get("api", {})
    method = api.get("method", "GET").upper()
    endpoint = api.get("endpoint", "/models")
    payload = inp.get("payload", {})

    # Dispatch internally to the rvc-python API
    if method == "GET":
        resp = client.get(endpoint, params=payload)
    else:
        # Special handling if calling /convert: expect base64 audio in payload
        if endpoint.startswith("/convert"):
            # Example payload expected: {"file_b64": "data:audio/wav;base64,...", "speaker_id": 0}
            files = {}
            data = {}
            file_b64 = payload.get("file_b64")
            if file_b64:
                header, encoded = file_b64.split(",", 1)
                audio_bytes = base64.b64decode(encoded)
                # rvc-python expects multipart form; simulate upload
                files["file"] = ("input.wav", io.BytesIO(audio_bytes), "audio/wav")
            speaker_id = payload.get("speaker_id", 0)
            data["speaker_id"] = speaker_id
            resp = client.post(endpoint, files=files, data=data)
        else:
            resp = client.post(endpoint, json=payload)

    # Return the response content (JSON or raw)
    try:
        return resp.json()
    except ValueError:
        return resp.content

# Start the serverless handler
runpod.serverless.start({"handler": handler})
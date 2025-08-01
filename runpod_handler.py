# runpod_handler.py
import runpod.serverless
import os
import base64
from pathlib import Path
from rvc_python.infer import RVCInference

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
    endpoint = api.get("endpoint", "/models")
    method = api.get("method", "GET").upper()
    payload = inp.get("payload", {})

    # List models
    if endpoint == "/models" and method == "GET":
        return list_models_directly()

    # Combined load-model + convert
    if endpoint == "/convert" and method == "POST":
        model_name = payload.get("model_name")
        audio_b64 = payload.get("audio_data")
        if not model_name or not audio_b64:
            return {"error": "Both model_name and audio_data are required for /convert"}

        model_dir = os.getenv("RVC_MODELDIR", "/runpod-volume/models")
        model_folder = Path(model_dir) / model_name

        if not model_folder.exists():
            return {"error": f"Model folder not found: {model_folder}"}

        # Discover .pth file inside
        pth_files = list(model_folder.glob("*.pth"))
        if not pth_files:
            return {"error": f"No .pth model found under {model_folder}"}
        model_path = str(pth_files[0])

        try:
            # Instantiate RVCInference and load model
            rvc = RVCInference(device="cuda:0")
            rvc.load_model(model_path)

            # Decode input audio
            audio_bytes = base64.b64decode(audio_b64)
            temp_in = "/tmp/input.wav"
            temp_out = "/tmp/output.wav"
            with open(temp_in, "wb") as f:
                f.write(audio_bytes)

            # Run inference (this uses the same interface as CLI)
            rvc.infer_file(temp_in, temp_out)

            # Read output and encode
            with open(temp_out, "rb") as f:
                out_bytes = f.read()
            out_b64 = base64.b64encode(out_bytes).decode("utf-8")
            return {"converted_audio": f"data:audio/wav;base64,{out_b64}"}

        except Exception as e:
            return {
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

    # Fallback
    return {"error": f"Unsupported endpoint/method combination: {method} {endpoint}"}

runpod.serverless.start({"handler": handler})

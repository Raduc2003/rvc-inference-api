# runpod_handler.py
import runpod.serverless
import os
import base64
from pathlib import Path
from shutil import copyfile
from rvc_python.infer import RVCInference

# Global caches
_inference_cache: dict[str, RVCInference] = {}          # model_name -> RVCInference instance
_model_params: dict[str, dict] = {}                    # model_name -> current param dict

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

def get_or_load_inference(model_name):
    """Load or retrieve cached RVCInference for a model."""
    if model_name in _inference_cache:
        return _inference_cache[model_name]
    model_dir = os.getenv("RVC_MODELDIR", "/runpod-volume/models")
    model_folder = Path(model_dir) / model_name
    if not model_folder.exists():
        raise FileNotFoundError(f"Model folder not found: {model_folder}")
    pth_files = list(model_folder.glob("*.pth"))
    if not pth_files:
        raise FileNotFoundError(f"No .pth model in {model_folder}")
    model_path = str(pth_files[0])

    rvc = RVCInference(device="cuda:0")
    rvc.load_model(model_path)
    _inference_cache[model_name] = rvc
    return rvc

def handler(job):
    inp = job.get("input", {})
    api = inp.get("api", {})
    endpoint = api.get("endpoint", "/models")
    method = api.get("method", "GET").upper()
    payload = inp.get("payload", {})

    # List models
    if endpoint == "/models" and method == "GET":
        return list_models_directly()

    # Set inference parameters for a model
    if endpoint == "/set_params" and method == "POST":
        model_name = payload.get("model_name")
        if not model_name:
            return {"error": "model_name is required for /set_params"}

        params = payload.get("params", {})
        if not isinstance(params, dict):
            return {"error": "params must be a dict"}

        _model_params[model_name] = params
        return {"updated": params}

    # Get current params
    if endpoint == "/get_params" and method == "POST":
        model_name = payload.get("model_name")
        if not model_name:
            return {"error": "model_name is required for /get_params"}
        return {"params": _model_params.get(model_name, {})}

    # Combined load-model + convert with inline or path-based input
if endpoint == "/convert" and method == "POST":
    print(f"[handler] /convert payload keys: {list(payload.keys())}")

    model_name = payload.get("model_name")
    audio_b64  = payload.get("audio_data")
    input_path = payload.get("input_path") or payload.get("path") or payload.get("key")

    if not model_name:
        return {"error": "model_name is required for /convert"}

    # load or retrieve inference
    try:
        rvc = get_or_load_inference(model_name)
    except Exception as e:
        return {"error_type": type(e).__name__, "error_message": str(e)}

    # apply stored params
    for k, v in _model_params.get(model_name, {}).items():
        try: setattr(rvc, k, v)
        except: pass

    temp_in  = "/tmp/input.wav"
    temp_out = "/tmp/output.wav"

    try:
        if audio_b64:
            print("[handler] decoding inline base64 audio_data")
            data = base64.b64decode(audio_b64)
            with open(temp_in, "wb") as f: f.write(data)

        elif input_path:
            print(f"[handler] using input_path: {input_path}")
            # resolve relative to the volume mount
            full = input_path if os.path.isabs(input_path) \
                else os.path.join("/runpod-volume", input_path.lstrip("/"))
            if not os.path.isfile(full):
                return {"error": f"input_path not found: {full}"}
            from shutil import copyfile
            copyfile(full, temp_in)

        else:
            return {"error": "Either audio_data or input_path is required"}

        # run inference
        rvc.infer_file(temp_in, temp_out)

        with open(temp_out, "rb") as f:
            out = f.read()
        out_b64 = base64.b64encode(out).decode("utf-8")
        return {"converted_audio": f"data:audio/wav;base64,{out_b64}"}

    except Exception as e:
        return {"error_type": type(e).__name__, "error_message": str(e)}

runpod.serverless.start({"handler": handler})

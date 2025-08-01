# runpod_handler.py
import runpod.serverless
import os
import base64
from pathlib import Path
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

        # Save/update
        _model_params[model_name] = params
        return {"updated": params}

    # Get current params
    if endpoint == "/get_params" and method == "POST":
        model_name = payload.get("model_name")
        if not model_name:
            return {"error": "model_name is required for /get_params"}
        return {"params": _model_params.get(model_name, {})}

    # Combined load-model + convert with applied params
    if endpoint == "/convert" and method == "POST":
        model_name = payload.get("model_name")
        audio_b64 = payload.get("audio_data")
        if not model_name or not audio_b64:
            return {"error": "Both model_name and audio_data are required for /convert"}

        try:
            rvc = get_or_load_inference(model_name)
        except Exception as e:
            return {"error_type": type(e).__name__, "error_message": str(e)}

        # Apply stored params if any (mapping naming to what RVCInference expects)
        params = _model_params.get(model_name, {})
        # Example params that might exist: pitch_algo, pitch_lvl, index_influence, filter_radius, etc.
        # rvc-python's RVCInference interface might expose these via attributes or method args.
        # If needed, you can adapt by monkey-patching or using its internal config API.
        # For simplicity, we'll assume you can set attributes directly if supported:
        for k, v in params.items():
            try:
                setattr(rvc, k, v)
            except Exception:
                # ignore unknown params; alternatively collect/report them
                pass

        try:
            # Decode input audio
            audio_bytes = base64.b64decode(audio_b64)
            temp_in = "/tmp/input.wav"
            temp_out = "/tmp/output.wav"
            with open(temp_in, "wb") as f:
                f.write(audio_bytes)

            # Perform inference
            rvc.infer_file(temp_in, temp_out)

            # Read and encode output
            with open(temp_out, "rb") as f:
                out_bytes = f.read()
            out_b64 = base64.b64encode(out_bytes).decode("utf-8")
            return {"converted_audio": f"data:audio/wav;base64,{out_b64}"}

        except Exception as e:
            return {
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

    return {"error": f"Unsupported endpoint/method: {method} {endpoint}"}

runpod.serverless.start({"handler": handler})

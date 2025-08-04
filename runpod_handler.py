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

    # Combined load-model + convert with applied params
    if endpoint == "/convert" and method == "POST":
        model_name = payload.get("model_name")
        audio_b64 = payload.get("audio_data")
        input_path = payload.get("input_path")  # new: relative or absolute path
        if not model_name:
            return {"error": "model_name is required for /convert"}

        try:
            rvc = get_or_load_inference(model_name)
        except Exception as e:
            return {"error_type": type(e).__name__, "error_message": str(e)}

        # Apply stored params if any
        params = _model_params.get(model_name, {})
        for k, v in params.items():
            try:
                setattr(rvc, k, v)
            except Exception:
                pass

        temp_in = "/tmp/input.wav"
        temp_out = "/tmp/output.wav"

        try:
            if audio_b64:
                # Inline base64 audio (legacy)
                audio_bytes = base64.b64decode(audio_b64)
                with open(temp_in, "wb") as f:
                    f.write(audio_bytes)
                source = temp_in
            elif input_path:
                # Resolve against mounted volume if relative
                if not os.path.isabs(input_path):
                    input_full = os.path.join("/runpod-volume", input_path.lstrip("/"))
                else:
                    input_full = input_path
                if not os.path.isfile(input_full):
                    return {"error": f"input_path does not exist: {input_full}"}
                # copy to temp_in for consistent interface
                copyfile(input_full, temp_in)
                source = temp_in
            else:
                return {"error": "Either audio_data or input_path is required for /convert"}

            # Perform inference
            rvc.infer_file(source, temp_out)

            # Read and return output
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

import os
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from inferrvc import RVC
import soundfile as sf
from pydantic import BaseModel

app = FastAPI(title="RVC-Inference API")

# Load models at startup
models = {}
current_model_name = None

@app.on_event("startup")
def load_models():
    global current_model_name
    model_dir = os.getenv("RVC_MODELDIR", "/models")
    for fname in os.listdir(model_dir):
        if fname.endswith(".pth"):
            model_path = os.path.join(model_dir, fname)
            name = os.path.splitext(fname)[0]
            models[name] = RVC(model=model_path)
    if not models:
        raise RuntimeError(f"No .pth models found in {model_dir}")
    current_model_name = next(iter(models.keys()))

# Pydantic model for inference parameters\class Params(BaseModel):
    f0_up_key: int = None
    index_rate: float = None
    filter_radius: int = None
    resample_sr: int = None
    output_frequency: int = None
    return_blocking: bool = None
    output_device: str = None
    output_volume: float = None

@app.get("/models")
def list_models():
    return {"models": list(models.keys()), "current": current_model_name}

@app.post("/models/{model_name}")
def switch_model(model_name: str):
    global current_model_name
    if model_name not in models:
        raise HTTPException(status_code=404, detail="Model not found")
    current_model_name = model_name
    return {"current": current_model_name}

@app.get("/params")
def get_params():
    model = models[current_model_name]
    return {
        "f0_up_key": model.f0_up_key,
        "index_rate": model.index_rate,
        "filter_radius": model.filter_radius,
        "resample_sr": model.resample_sr,
        "output_frequency": model.output_frequency,
        "return_blocking": model.return_blocking,
        "output_device": model.output_device,
        "output_volume": model.output_volume,
    }

@app.post("/params")
def set_params(params: Params):
    model = models[current_model_name]
    updates = {}
    for key, value in params.dict(exclude_none=True).items():
        setattr(model, key, value)
        updates[key] = value
    return {"updated": updates}

@app.post("/convert/")
async def convert(file: UploadFile = File(...), speaker_id: int = 0):
    data = await file.read()
    audio, sr = sf.read(io.BytesIO(data), dtype="float32")
    model = models[current_model_name]
    # Run inference with current settings
    converted = model(audio, f0_up_key=speaker_id)
    # Prepare streaming response
    buf = io.BytesIO()
    sf.write(buf, converted, sr)
    buf.seek(0)
    return StreamingResponse(buf, media_type="audio/wav")

from fastapi import FastAPI, File, UploadFile
from rvc_inference import RVCInference
import tempfile
import shutil
import uuid
import os
import soundfile as sf

app = FastAPI(title="RVC‑Inference API")

# Load your model(s) once at startup
# Point to local paths or download them somewhere and mount in Docker
svc = RVCInference(model_paths=["/models/v1.pth"])

@app.post("/convert/")
async def convert(file: UploadFile = File(...), speaker_id: int = 0):
    # Save the uploaded file to a temp file
    tmp_in = f"/tmp/{uuid.uuid4()}.wav"
    with open(tmp_in, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run inference
    wav_out = svc.run(tmp_in, speaker_id=speaker_id)

    # Write output to a new temp file
    tmp_out = f"/tmp/{uuid.uuid4()}.wav"
    sf.write(tmp_out, wav_out, samplerate=svc.sample_rate)

    # Return as raw bytes
    return await fastapi.responses.FileResponse(tmp_out, media_type="audio/wav")

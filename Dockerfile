# ---------- Base Image ----------
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

# ---------- Install OS Packages ----------
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg sox python3.10-venv python3-pip git build-essential python3-dev && \
    rm -rf /var/lib/apt/lists/*

# ---------- Create Non-Root User ----------
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app
RUN chown -R appuser:appuser /home/appuser/app
USER appuser

# ---------- Python Virtual Environment ----------
RUN python3 -m venv venv
RUN venv/bin/pip install --no-cache-dir "pip==23.3.2"

# ---------- Dependencies for RVC-Inference ----------
# Install Fairseq fork (required by inferrvc on Python 3.10+)
RUN venv/bin/pip install \
    https://github.com/One-sixth/fairseq/archive/main.zip

# Install the official inferrvc wheel from CircuitCM's GitHub
RUN venv/bin/pip install \
    https://github.com/CircuitCM/RVC-inference/raw/main/dist/inferrvc-1.0-py3-none-any.whl \
    --no-cache-dir

# Install FastAPI, Uvicorn, and audio libs
COPY requirements.txt .
RUN venv/bin/pip install --no-cache-dir -r requirements.txt

# Force reinstall GPU-enabled PyTorch & TorchAudio for CUDA 12.1
RUN venv/bin/pip install --force-reinstall --no-cache-dir \
    torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# ---------- Application Code ----------
COPY app/main.py .

# ---------- Runtime Configuration ----------
EXPOSE 5050
ENV RVC_MODELDIR=/models

# Launch the FastAPI app
CMD ["/home/appuser/app/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5050"]

# ---------- Base Image (CUDA 12.1 Runtime) ----------
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# ---------- Install OS Dependencies ----------
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.10 python3.10-venv python3-pip \
        ffmpeg sox git \
        build-essential python3-dev libsndfile1-dev && \
    rm -rf /var/lib/apt/lists/*

# ---------- Create Non-Root User ----------
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app
RUN chown -R appuser:appuser /home/appuser/app
USER appuser

# ---------- Python Virtual Environment ----------
RUN python3.10 -m venv venv
ENV PATH="/home/appuser/app/venv/bin:$PATH"
# Pin pip below 24.1 to avoid omegaconf metadata errors
RUN pip install --upgrade "pip==23.3.2"

# ---------- Install rvc-python & Dependencies ----------
# CPU + API support (includes Fairseq, pyworld, etc.)
RUN pip install rvc-python

# GPU-accelerated PyTorch & TorchAudio for CUDA 12.1
RUN pip install --no-cache-dir \
        torch torchaudio \
        --index-url https://download.pytorch.org/whl/cu121

# ---------- Configure Model Directory ----------
# Set environment variable for RVC to locate models on the attached network volume
ENV RVC_MODELDIR=/runpod-volume/models
# Create a symlink so legacy paths (/models) work if referenced in code
RUN ln -s /runpod-volume/models /models || true

# ---------- Expose API Port ----------
EXPOSE 5050

# ---------- Launch the rvc-python API Server ----------
# -p 5050 : serve on port 5050
# -l      : allow external connections
CMD ["python3", "-m", "rvc_python", "api", "-p", "5050", "-l"]

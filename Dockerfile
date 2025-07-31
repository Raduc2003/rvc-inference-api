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
# install the fixed rvc-python release and required extras
RUN pip install "rvc-python==0.1.5" python-multipart


# GPU-accelerated PyTorch & TorchAudio for CUDA 12.1
RUN pip install --no-cache-dir \
        torch torchaudio \
        --index-url https://download.pytorch.org/whl/cu121

# ---------- Configure Model Directory ----------
# Set environment variable for RVC to locate models on the attached network volume
ENV RVC_MODELDIR=/runpod-volume/models
# Create a symlink so legacy paths (/models) work if referenced in code
RUN ln -s /runpod-volume/models /rvc_models || true

# ---------- Expose API Port ----------
EXPOSE 5050

# copy the handler into the image
COPY runpod_handler.py .

# install runpod SDK (needed for serverless handler) and any extras
RUN pip install runpod

# entrypoint: run the handler (not the built-in HTTP server)
CMD ["python3", "-u", "runpod_handler.py"]



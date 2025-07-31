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
# Pin pip below 24.1 to avoid omegaconf metadata issues
RUN pip install --upgrade "pip==23.3.2"

# ---------- Install Python Dependencies # ---------- Install Python Dependencies ----------
# rvc-python fixed release + extras and runpod SDK
RUN pip install --no-cache-dir \
    runpod "rvc-python==0.1.5" python-multipart tensorboardX

# GPU-accelerated PyTorch & TorchAudio for CUDA 12.1 (actual available versions)
RUN pip install --no-cache-dir \
    torch==2.5.1+cu121 torchaudio==2.5.1+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# ---------- Configure Model Directory ----------
ENV RVC_MODELDIR=/runpod-volume/models
# Fallback symlinks for legacy expectations
RUN ln -s /runpod-volume/models /models || true && \
    ln -s /runpod-volume/models /rvc_models || true

# ---------- Copy handler ----------
COPY runpod_handler.py .
COPY dump_api_exports.py .

# ---------- Expose Port (harmless for serverless) ----------
EXPOSE 5050

# ---------- Entry Point ----------
#CMD ["python3", "-u", "runpod_handler.py"]
CMD ["python3", "-u", "dump_api_exports.py"]
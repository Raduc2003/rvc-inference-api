# ---------- Base Image (CUDA 12.1.1 on Ubuntu 22.04) ----------
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# ---------- Install OS Dependencies ----------
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.10 python3.10-venv python3-pip ffmpeg sox git && \
    rm -rf /var/lib/apt/lists/*

# ---------- Create and Use Non‑Root User ----------
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# ---------- Python Virtual Environment ----------
RUN python3.10 -m venv venv
ENV PATH="/home/appuser/app/venv/bin:$PATH"
RUN pip install --upgrade pip

# ---------- Install rvc‑python and GPU‑enabled PyTorch ----------
RUN pip install rvc-python                          # CPU+API support :contentReference[oaicite:0]{index=0}  
RUN pip install torch==2.1.1+cu118 \
                torchaudio==2.1.1+cu118 \
                --index-url https://download.pytorch.org/whl/cu118  # GPU accel :contentReference[oaicite:1]{index=1}

# ---------- Expose API Port ----------
EXPOSE 5050

# ---------- Launch rvc‑python API Server ----------
CMD ["python3", "-m", "rvc_python", "api", "-p", "5050", "-l"]  # start API server :contentReference[oaicite:2]{index=2}

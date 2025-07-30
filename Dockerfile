# ---------- Base Image (CUDA Runtime) ----------
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# ---------- Install OS Dependencies ----------
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3.10 python3.10-venv python3-pip ffmpeg sox git && \
    rm -rf /var/lib/apt/lists/*

# ---------- Non-Root User Setup ----------
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app
RUN chown -R appuser:appuser /home/appuser/app
USER appuser

# ---------- Python Virtual Environment & pip Pinning ----------
RUN python3.10 -m venv venv
ENV PATH="/home/appuser/app/venv/bin:$PATH"
# Pin pip to <24.1 to avoid metadata errors with omegaconf==2.0.6
RUN pip install --upgrade "pip==23.3.2"                      

# ---------- Install rvc-python & GPU PyTorch ----------
RUN pip install rvc-python                                  # CPU+API support :contentReference[oaicite:5]{index=5}
RUN pip install torch==2.1.1+cu118 \
                torchaudio==2.1.1+cu118 \
                --index-url https://download.pytorch.org/whl/cu118  # GPU support :contentReference[oaicite:6]{index=6}

# ---------- Expose API Port ----------
EXPOSE 5050

# ---------- Launch the rvc-python API Server ----------
# -p 5050 : bind to port 5050
# -l      : allow external connections
CMD ["python3", "-m", "rvc_python", "api", "-p", "5050", "-l"]  # start API server :contentReference[oaicite:7]{index=7}

FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg sox python3.10-venv python3-pip git build-essential python3-dev && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app
RUN chown -R appuser:appuser /home/appuser/app
USER appuser

# Python venv
RUN python3 -m venv venv
RUN venv/bin/pip install --no-cache-dir "pip==23.3.2"

# Fairseq for RVC-inference
RUN venv/bin/pip install \
    https://github.com/One-sixth/fairseq/archive/main.zip

# Copy & install deps (including the RVC wheel)
COPY requirements.txt .
RUN venv/bin/pip install --no-cache-dir -r requirements.txt

# Install GPU-enabled PyTorch
RUN venv/bin/pip install --force-reinstall --no-cache-dir \
    torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Copy code
COPY app/main.py .

EXPOSE 5050
ENV RVC_MODELDIR=/models

CMD ["/home/appuser/app/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5050"]

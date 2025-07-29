# ---------- base image ----------
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

# ---------- OS packages & non-root user ----------
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg sox python3.10-venv python3-pip git build-essential python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user and grant ownership of the app directory
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app
RUN chown -R appuser:appuser /home/appuser/app

# Switch to the non-root user
USER appuser

# ---------- Python Installation ----------

# Create the virtual environment
RUN python3 -m venv venv

# Install a specific, older version of pip for compatibility
RUN venv/bin/pip install --no-cache-dir "pip==23.3.2"

# Copy and install rvc-python and its dependencies.
# This will succeed now that all build tools are installed.
COPY requirements.txt .
RUN venv/bin/pip install --no-cache-dir -r requirements.txt

# Now, FORCE the installation of the correct GPU-enabled torch.
RUN venv/bin/pip install --force-reinstall --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# ---------- Models & Launcher ----------
RUN mkdir -p ./rvc_models/rmvpe

# ---------- Runtime Config ----------
EXPOSE 5050

# Use the python -m command to start the API directly
CMD ["/home/appuser/app/venv/bin/python", "-m", "rvc.api", "--host", "0.0.0.0", "--port", "5050", "--device", "cuda:0", "--models_path", "rvc_models"]

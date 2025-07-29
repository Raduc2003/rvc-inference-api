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

# Copy and install all Python dependencies
COPY requirements.txt .
RUN venv/bin/pip install --no-cache-dir -r requirements.txt

# Now, FORCE the installation of the correct GPU-enabled torch.
RUN venv/bin/pip install --force-reinstall --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# ---------- Application Setup ----------
# Copy your FastAPI application code into the container
COPY main.py .

# ---------- Runtime Config ----------
EXPOSE 5050

# Set the default model directory used by your main.py script
ENV RVC_MODELDIR=/models

# Run the FastAPI app with Uvicorn
CMD ["/home/appuser/app/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5050"]

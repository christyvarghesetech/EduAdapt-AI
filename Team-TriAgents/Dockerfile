FROM python:3.12-slim

# Prevent Python from writing pyc files and buffer output for container stability
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies required for native packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Expose the API port
EXPOSE 8000

# Run uvicorn server in unbuffered mode
CMD uvicorn api:app --host 0.0.0.0 --port $PORT

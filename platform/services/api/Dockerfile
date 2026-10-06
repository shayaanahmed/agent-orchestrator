FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY ./requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser \
    && mkdir -p /data/artifacts \
    && chown -R appuser:appuser /data
USER appuser

# Expose port
EXPOSE 8000

# Run through the package bootstrap because this repository's top-level
# "platform" namespace shares a name with Python's standard-library module.
CMD ["python", "services/api/entrypoint.py"]

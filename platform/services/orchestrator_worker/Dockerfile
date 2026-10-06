FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app/platform
ENV PYTHONPATH=/app/platform PYTHONUNBUFFERED=1
RUN adduser --disabled-password --gecos '' appuser && mkdir -p /data/artifacts && chown -R appuser:appuser /data
USER appuser
CMD ["python", "-m", "services.orchestrator_worker.main"]

FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-pytest python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    "fastapi>=0.104,<1" "uvicorn[standard]>=0.24,<1" "pydantic>=2.5,<3"
COPY services/sandbox_controller /app/services/sandbox_controller

RUN mkdir -p /data/artifacts && chown -R node:node /app /data/artifacts
USER node
EXPOSE 8090
CMD ["python3", "-m", "uvicorn", "services.sandbox_controller.main:app", "--host", "0.0.0.0", "--port", "8090"]

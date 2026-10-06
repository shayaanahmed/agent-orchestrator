FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app/platform
ENV PYTHONPATH=/app/platform PYTHONUNBUFFERED=1
RUN adduser --disabled-password --gecos '' appuser
USER appuser
EXPOSE 8080
CMD ["uvicorn", "services.model_gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]

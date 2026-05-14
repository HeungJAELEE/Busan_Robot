FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pymcprotocol
COPY services/plc_bridge/ .
CMD ["python", "services/plc_bridge/main.py"]

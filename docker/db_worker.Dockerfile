FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY infrastructure/repositories/database_repository.py ./infrastructure/repositories/
COPY services/db_worker/ .
CMD ["python", "services/db_worker/main.py"]

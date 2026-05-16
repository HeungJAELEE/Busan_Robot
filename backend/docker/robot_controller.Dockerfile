FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/robot_controller/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/robot_controller/src ./src
COPY frontend/indy_utils ./src/infrastructure/indy_utils

CMD ["python", "-m", "src.main"]

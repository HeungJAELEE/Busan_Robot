# YOLO/OpenCV 등 GPU 가속이 필요할 경우 PyTorch/CUDA 베이스 이미지를 권장합니다.
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/vision_yolo/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/vision_yolo/src ./src

CMD ["python", "-m", "src.main"]

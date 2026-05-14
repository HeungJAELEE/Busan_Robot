# YOLO/OpenCV 등 GPU 가속이 필요할 경우 PyTorch/CUDA 베이스 이미지를 권장합니다.
FROM python:3.10-slim
WORKDIR /app
# RUN pip install opencv-python-headless torch torchvision ultralytics paho-mqtt
COPY services/vision_yolo/ .
CMD ["python", "services/vision_yolo/main.py"]

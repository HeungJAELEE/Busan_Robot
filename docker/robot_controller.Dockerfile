FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 로봇 통신 모듈만 복사
COPY core/domains/robot/ ./core/domains/robot/
COPY services/robot_controller/ ./services/robot_controller/
CMD ["python", "services/robot_controller/main.py"]

FROM python:3.11-slim
WORKDIR /app
# Node.js 등 웹 뷰어 서버를 구축할 수도 있습니다.
COPY services/digital_twin/ .
CMD ["python", "services/digital_twin/main.py"]

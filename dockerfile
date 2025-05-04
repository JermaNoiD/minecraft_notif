FROM python:3.9-slim
WORKDIR /app
COPY minecraft_ntfy.py .
RUN pip install requests
CMD ["python", "minecraft_ntfy.py"]

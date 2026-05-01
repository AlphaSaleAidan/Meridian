FROM ultralytics/ultralytics:latest-jetson-jetpack5

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY edge_agent.py .
COPY config/ config/

CMD ["python", "edge_agent.py"]

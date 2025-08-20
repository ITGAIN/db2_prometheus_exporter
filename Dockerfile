FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exporter.py .
COPY config.yaml .

EXPOSE 8000

CMD ["python", "exporter.py"]
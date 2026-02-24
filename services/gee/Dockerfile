FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default to terrain extraction; override with CMD for verification
ENTRYPOINT ["python"]
CMD ["extract_terrain.py"]

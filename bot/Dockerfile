# 1. Use lightweight Python
FROM python:3.11-slim

# 2. Settings
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 3. Install dependencies (requests, boto3)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Code
COPY main.py .

# 5. Run
CMD ["python", "main.py"]
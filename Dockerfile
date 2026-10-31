FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501

WORKDIR /app

# Install curl/build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure data directory exists and is writable
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Create and use non-root user (compatible with Hugging Face Spaces and Render)
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

EXPOSE 8501 7860

CMD ["python", "run.py"]

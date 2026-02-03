# Use Python 3.9 Slim as the base image
FROM python:3.9-slim

# Install system dependencies (FFmpeg is required)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port (Cloud Run sets PORT env var, but this is good documentation)
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
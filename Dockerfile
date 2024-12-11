# Use the official Python 3.7 slim image as base
FROM python:3.7-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies individually to simplify troubleshooting
RUN pip install --no-cache-dir flask
RUN pip install --no-cache-dir pandas
RUN pip install --no-cache-dir scipy
RUN pip install --no-cache-dir openpyxl
RUN pip install --no-cache-dir requests

# Run the Flask application
CMD ["python", "app.py"]

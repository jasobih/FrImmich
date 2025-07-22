# Use a lightweight Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends     libjpeg-dev     zlib1g-dev     cmake     build-essential     libboost-python-dev     libboost-thread-dev     libx11-dev     libatlas-base-dev     && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user and group
RUN addgroup --system app && adduser --system --group app

# Create necessary directories and set permissions
RUN mkdir -p /app/data /tmp/faces &&     chown -R app:app /app /tmp/faces

# Switch to the non-root user
USER app

# Copy the application source code
COPY ./app /app/app

# Expose the port the app runs on (the port here should match the gunicorn bind port)
EXPOSE 8080

# Define the command to run the application using a production server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "-w", "1", "app.app:create_app()"]

# Use lightweight official Python runtime as base
FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable instant stdout logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a workspace directory inside the container
WORKDIR /app

# Install system dependencies if any are needed (none for pure Python)
# Copy requirements first to leverage Docker's caching mechanism
COPY requirements.txt .

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files to workspace
COPY . .

# Create a non-privileged user and group for security best-practices
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose Flask API server port
EXPOSE 5000

# Run the application with production-grade WSGI server Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

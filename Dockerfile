# SearchSift Backend Dockerfile
#
# Build:
#   docker build -t searchsift .
#
# Run:
#   docker run -p 5000:5000 -v $(pwd)/data:/app/data -v $(pwd)/reports:/app/reports searchsift
#
# Note: Binds to 127.0.0.1 by default for security.
# For container networking, you may need to bind to 0.0.0.0

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Create directories for data and reports
RUN mkdir -p data reports logs

# Set environment variables
ENV FLASK_APP=backend/app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')" || exit 1

# Run the application
# Note: Using 127.0.0.1 for security. Change to 0.0.0.0 if needed for container networking.
CMD ["python", "-m", "flask", "run", "--host=127.0.0.1", "--port=5000"]

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY . .

# Create static files directory
RUN mkdir -p staticfiles
RUN python manage.py collectstatic --noinput

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Expose ports
EXPOSE 8000 8501

# Create a non-root user
RUN useradd -m -s /bin/bash app_user && \
    chown -R app_user:app_user /app
USER app_user

# Start both Django and Streamlit
CMD ["sh", "-c", "streamlit run faucet/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.baseUrlPath \"\" --server.enableCORS false --server.enableXsrfProtection false & python manage.py runserver 0.0.0.0:8000"] 
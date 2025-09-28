FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssh-client \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*


# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY setup.py .
COPY README.md .

# Install the application
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -s /bin/bash pxrun && \
    mkdir -p /home/pxrun/.ssh && \
    chown -R pxrun:pxrun /home/pxrun

# Switch to non-root user
USER pxrun

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Default command
ENTRYPOINT ["pxrun"]
CMD ["--help"]
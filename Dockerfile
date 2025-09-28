FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    openssh-client \
    git \
    curl \
    make \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./
RUN /root/.cargo/bin/uv pip install --system --no-cache -r requirements-dev.txt

# Copy application code
COPY . .

# Install the application in development mode
RUN /root/.cargo/bin/uv pip install --system --no-cache -e .

# Create non-root user
RUN useradd -m -s /bin/bash pxrun && \
    mkdir -p /home/pxrun/.ssh && \
    chown -R pxrun:pxrun /home/pxrun

# Switch to non-root user
USER pxrun

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV PYTHONDONTWRITEBYTECODE=1

# Default command
ENTRYPOINT ["pxrun"]
CMD ["--help"]
# Hardened isolated sandbox container for VERIQ
FROM python:3.11-slim

# Install minimal test runner dependencies
RUN pip install --no-cache-dir pytest==8.3.3

# Create non-privileged user and restricted workspace
RUN groupadd -g 1000 veriq && \
    useradd -u 1000 -g veriq -m -s /bin/bash veriq

WORKDIR /workspace

# Switch to non-root execution
USER veriq

# Default command
CMD ["pytest", "-v"]

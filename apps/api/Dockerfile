FROM python:3.12-slim

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packages and requirements
COPY packages/ packages/
COPY apps/api/requirements.txt requirements.txt

# Install dependencies and shared packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install -e packages/evaluation-specifications

# Copy API and Execution Runner source code
COPY apps/api/ apps/api/
COPY apps/execution-runner/ apps/execution-runner/
COPY alembic.ini alembic.ini

WORKDIR /workspace/apps/api
ENV PYTHONPATH="/workspace/apps/api:/workspace/apps/execution-runner"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

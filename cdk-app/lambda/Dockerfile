# Use Python 3.9 slim image as base
FROM python:3.9-slim as builder

# Install poetry
RUN pip install poetry

# Set working directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to create virtual environment in the project directory
RUN poetry config virtualenvs.in-project true

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Development stage
FROM builder as development
RUN poetry install --no-interaction --no-ansi

# Production stage
FROM python:3.9-slim as production

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

# Set PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Set Python path
ENV PYTHONPATH=/app

# Command to run the application
CMD ["python", "-m", "chat"]

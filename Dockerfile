# Pratham Bank · Mitr — multilingual voice banking agent
# Single image that runs the FastAPI backend (which also serves the frontend)
# and can run the one-time Elastic setup scripts.
FROM python:3.11-slim

# Keep Python lean and unbuffered (logs stream immediately)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# The backend imports sibling modules and serves ../frontend
WORKDIR /app/backend

EXPOSE 8000

# Default: run the web server. (The 'setup' compose service overrides this.)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

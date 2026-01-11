FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . /app

# Set a default port environment variable expected by many hosts
ENV PORT 8080

# Use gunicorn to serve the app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "2"]

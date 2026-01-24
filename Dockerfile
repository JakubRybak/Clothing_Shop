# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8080

# Set work directory
WORKDIR /app

# Install system dependencies for psycopg2 and other tools
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Expose the port Cloud Run expects
EXPOSE 8080

# Run the application using gunicorn
# Replace 'Clothing_Shop.wsgi:application' with your actual wsgi path if different
CMD exec gunicorn Clothing_Shop.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0

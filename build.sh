#!/bin/bash

echo "🚀 Starting Railway Build..."

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput
gunicorn core.wsgi:application --bind 0.0.0.0:8000
echo "✅ Build completed successfully!"
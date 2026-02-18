#!/usr/bin/env bash
set -o errexit  # exit on first error

# Upgrade pip first
pip install --upgrade pip

# Install project dependencies from requirements.txt
if [ -f requirements.txt ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

# Collect static files (for WhiteNoise / production)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "Running migrations..."
python manage.py migrate

echo "Build finished successfully!"

# Start the Django app with Gunicorn
echo "Starting Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT

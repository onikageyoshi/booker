#!/usr/bin/env bash
set -o errexit

# Install Poetry
pip install poetry

# Prevent Poetry from creating virtualenv
poetry config virtualenvs.create false

# Install dependencies
poetry install --no-root --no-interaction --no-ansi


# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

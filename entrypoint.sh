#!/bin/sh
set -e

PORT="${PORT:-8000}"

if [ "$1" = "web" ]; then
    echo "Running migrations..."
    python manage.py migrate
    echo "Running system checks..."
    python manage.py check
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
    echo "Creating superuser..."
    python create_superuser.py
    echo "Starting gunicorn on 0.0.0.0:${PORT}..."
    exec gunicorn resume_builder.wsgi:application --bind "0.0.0.0:${PORT}" --workers "${GUNICORN_WORKERS:-1}" --timeout 120
elif [ "$1" = "celery" ]; then
    echo "Starting celery worker..."
    exec celery -A resume_builder worker -l info --concurrency 1
else
    echo "Usage: entrypoint.sh [web|celery]"
    exit 1
fi

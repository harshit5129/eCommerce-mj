#!/bin/sh
set -e

echo "Waiting for database..."
sleep 3

echo "Running migrations..."
python manage.py migrate --noinput || {
    echo "Migration failed, retrying in 5 seconds..."
    sleep 5
    python manage.py migrate --noinput
}

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || true

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 120

#!/bin/bash
# Build script for Vercel - runs migrations and collects static files

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --settings=config.settings.vercel --run-syncdb

echo "Collecting static files..."
python manage.py collectstatic --settings=config.settings.vercel --noinput

echo "Build completed!"

#!/bin/bash
# Build script for Vercel deployment

echo "Starting build process..."

# Install dependencies
pip install -r requirements.txt

# Run migrations (creates SQLite database)
python manage.py migrate --settings=config.settings.vercel --run-syncdb

# Collect static files
python manage.py collectstatic --settings=config.settings.vercel --noinput

echo "Build completed!"

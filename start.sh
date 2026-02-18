#!/bin/bash

# E-Commerce Application Startup Script

echo "=================================================="
echo "  E-Commerce Application Startup"
echo "=================================================="

# Check if MongoDB is running
if ! pgrep -x "mongod" > /dev/null; then
    echo "⚠ MongoDB is not running. Starting MongoDB..."
    mkdir -p /data/db
    mongod --fork --logpath /var/log/mongodb.log
    sleep 2
    echo "✓ MongoDB started"
else
    echo "✓ MongoDB is already running"
fi

# Navigate to project directory
cd /root/Desktop/ecomm/ecomm

# Activate virtual environment
source venv/bin/activate

echo ""
echo "✓ Virtual environment activated"
echo "✓ Starting Django development server..."
echo ""
echo "=================================================="
echo "  Access the application at:"
echo "  http://localhost:8000"
echo ""
echo "  Admin credentials:"
echo "  Email: admin@example.com"
echo "  Password: admin123"
echo "=================================================="
echo ""

# Start Django server
python manage.py runserver 0.0.0.0:8000

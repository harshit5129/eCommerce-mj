#!/bin/bash

# E-Commerce Application Startup Script

echo "=================================================="
echo "  E-Commerce Application Startup"
echo "=================================================="

# Navigate to project directory
cd /root/Desktop/ecomm/ecomm

# Activate virtual environment
source venv/bin/activate

echo "✓ Virtual environment activated"

# Check if Redis is installed and start it (optional, for caching)
if command -v redis-server &> /dev/null; then
    if ! pgrep -x "redis-server" > /dev/null; then
        echo "⚠ Redis is not running. Starting Redis..."
        redis-server --daemonize yes
        sleep 1
        echo "✓ Redis started on port 6379"
    else
        echo "✓ Redis is already running"
    fi
else
    echo "⚠ Redis not installed. Cache will use DummyCache (no persistence)"
fi

echo ""
echo "✓ Starting Django development server..."
echo ""
echo "=================================================="
echo "  Access the application at:"
echo "  http://localhost:8000"
echo ""
echo "  Admin Panel:"
echo "  http://localhost:8000/admin/"
echo ""
echo "  Admin credentials:"
echo "  Email: admin@example.com"
echo "  Password: admin123"
echo ""
echo "  Available Test Coupons:"
echo "  • WELCOME10  - 10% off"
echo "  • SAVE20     - 20% off (min ₹2000)"
echo "  • FLAT100    - ₹100 off"
echo ""
echo "  Payment Method:"
echo "  • Razorpay Online Payment (Card/UPI/NetBanking/Wallet)"
echo ""
echo "  NOTE: Configure Razorpay keys in .env file"
echo "  Get test keys from: https://dashboard.razorpay.com/app/keys"
echo "=================================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start Django server
python manage.py runserver 0.0.0.0:8000

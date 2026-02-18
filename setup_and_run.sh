#!/bin/bash

# Complete Django PostgreSQL Setup and Run Script
# This script sets up the entire application and runs it

set -e

echo "=========================================="
echo "Django PostgreSQL E-Commerce Setup"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Change to project directory
cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python found${NC}"

# Check PostgreSQL
echo ""
echo -e "${BLUE}Checking PostgreSQL...${NC}"
if ! command -v psql &> /dev/null; then
    echo -e "${RED}✗ PostgreSQL is not installed${NC}"
    echo "Install PostgreSQL first:"
    echo "  Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
    echo "  macOS: brew install postgresql"
    exit 1
fi

# Check if PostgreSQL is running
if ! pg_isready -q 2>/dev/null; then
    echo -e "${YELLOW}⚠ PostgreSQL is not running. Attempting to start...${NC}"
    sudo service postgresql start 2>/dev/null || sudo systemctl start postgresql 2>/dev/null || pg_ctl start -D /usr/local/var/postgres 2>/dev/null || true
    
    sleep 2
    
    if ! pg_isready -q 2>/dev/null; then
        echo -e "${RED}✗ Could not start PostgreSQL${NC}"
        echo "Please start PostgreSQL manually:"
        echo "  sudo service postgresql start"
        exit 1
    fi
fi

echo -e "${GREEN}✓ PostgreSQL is running${NC}"

# Install dependencies
echo ""
echo -e "${BLUE}Installing dependencies...${NC}"
pip install -q -r requirements-postgres.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Database configuration
DB_NAME="ecomm_db"
DB_USER="postgres"
DB_PASS="postgres"
DB_HOST="localhost"
DB_PORT="5432"

# Create database
echo ""
echo -e "${BLUE}Setting up database...${NC}"

# Check if database exists
if sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" 2>/dev/null | grep -q 1; then
    echo -e "${YELLOW}Database ${DB_NAME} already exists. Dropping and recreating...${NC}"
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${DB_NAME}" 2>/dev/null
fi

# Create database
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME}" 2>/dev/null
echo -e "${GREEN}✓ Database ${DB_NAME} created${NC}"

# Enable extensions
sudo -u postgres psql -d ${DB_NAME} -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" 2>/dev/null
sudo -u postgres psql -d ${DB_NAME} -c "CREATE EXTENSION IF NOT EXISTS btree_gin;" 2>/dev/null
echo -e "${GREEN}✓ Database extensions enabled${NC}"

# Create migrations
echo ""
echo -e "${BLUE}Creating migrations...${NC}"
python3 manage.py makemigrations users products orders offers cart --noinput
echo -e "${GREEN}✓ Migrations created${NC}"

# Apply migrations
echo ""
echo -e "${BLUE}Applying migrations...${NC}"
python3 manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations applied${NC}"

# Collect static
echo ""
echo -e "${BLUE}Collecting static files...${NC}"
python3 manage.py collectstatic --noinput 2>/dev/null || echo -e "${YELLOW}⚠ Static collection skipped (optional)${NC}"

# Generate test data
echo ""
echo -e "${BLUE}Generating test data...${NC}"
python3 generate_test_data.py
echo -e "${GREEN}✓ Test data generated${NC}"

# Create superuser if doesn't exist
echo ""
echo -e "${BLUE}Creating superuser...${NC}"
python3 << PYEOF
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from users.models import User

if not User.objects.filter(email='admin@example.com').exists():
    User.objects.create_superuser(
        email='admin@example.com',
        username='admin',
        password='admin123',
        first_name='Admin',
        last_name='User'
    )
    print("Superuser created: admin@example.com / admin123")
else:
    print("Superuser already exists")
PYEOF

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}Application URLs:${NC}"
echo "  • Website:     http://localhost:8000"
echo "  • Admin:       http://localhost:8000/admin/"
echo "  • API:         http://localhost:8000/api/"
echo ""
echo -e "${BLUE}Login Credentials:${NC}"
echo "  • Admin:       admin@example.com / admin123"
echo ""
echo -e "${BLUE}Test Coupons:${NC}"
echo "  • WELCOME10  - 10% off"
echo "  • SAVE20     - 20% off (min ₹2000)"
echo "  • FLAT100    - ₹100 off"
echo ""
echo -e "${GREEN}Starting server...${NC}"
echo "=========================================="
echo ""

# Run the server
python3 manage.py runserver 0.0.0.0:8000

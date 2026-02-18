#!/bin/bash

# PostgreSQL Migration Setup Script
# This script helps you migrate from MongoDB to PostgreSQL

set -e

echo "=========================================="
echo "PostgreSQL Migration Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}✗ PostgreSQL is not installed${NC}"
    echo "Please install PostgreSQL first:"
    echo "  Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
    echo "  macOS: brew install postgresql"
    echo "  Windows: Download from postgresql.org"
    exit 1
fi

echo -e "${GREEN}✓ PostgreSQL is installed${NC}"

# Check if Redis is installed
if ! command -v redis-cli &> /dev/null; then
    echo -e "${YELLOW}⚠ Redis is not installed (optional but recommended)${NC}"
    echo "For caching and Celery, install Redis:"
    echo "  Ubuntu/Debian: sudo apt-get install redis-server"
    echo "  macOS: brew install redis"
fi

# Setup PostgreSQL database
echo ""
echo "Setting up PostgreSQL database..."
echo ""

read -p "Enter PostgreSQL database name [ecomm_db]: " DB_NAME
DB_NAME=${DB_NAME:-ecomm_db}

read -p "Enter PostgreSQL user [postgres]: " DB_USER
DB_USER=${DB_USER:-postgres}

read -s -p "Enter PostgreSQL password: " DB_PASS
echo ""

read -p "Enter PostgreSQL host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "Enter PostgreSQL port [5432]: " DB_PORT
DB_PORT=${DB_PORT:-5432}

# Create database
echo ""
echo "Creating database..."
if PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1; then
    echo -e "${YELLOW}Database $DB_NAME already exists${NC}"
    read -p "Drop and recreate? (y/N): " DROP_DB
    if [[ $DROP_DB =~ ^[Yy]$ ]]; then
        PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME"
        PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME"
        echo -e "${GREEN}✓ Database recreated${NC}"
    fi
else
    PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME"
    echo -e "${GREEN}✓ Database created${NC}"
fi

# Enable required PostgreSQL extensions
echo ""
echo "Enabling PostgreSQL extensions..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS btree_gin;"
echo -e "${GREEN}✓ Extensions enabled${NC}"

# Update .env file
echo ""
echo "Updating .env file..."

if [ -f .env ]; then
    # Backup existing .env
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    
    # Remove old MongoDB settings
    sed -i '/^MONGODB_/d' .env
    
    # Add new PostgreSQL settings
    cat >> .env << EOF

# PostgreSQL Configuration
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT

# Redis Configuration (optional)
REDIS_URL=redis://127.0.0.1:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
EOF
    
    echo -e "${GREEN}✓ .env file updated${NC}"
else
    cat > .env << EOF
# Django Settings
SECRET_KEY=change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL Configuration
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASS
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT

# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# Email Settings
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=

# Site Settings
SITE_NAME=E-Commerce Store
SITE_URL=http://localhost:8000

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
EOF
    
    echo -e "${GREEN}✓ .env file created${NC}"
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements-postgres.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create migrations
echo ""
echo "Creating database migrations..."
python manage.py makemigrations users products orders offers cart
echo -e "${GREEN}✓ Migrations created${NC}"

# Apply migrations
echo ""
echo "Applying migrations..."
python manage.py migrate
echo -e "${GREEN}✓ Migrations applied${NC}"

# Create superuser
echo ""
echo "Creating superuser..."
python manage.py createsuperuser

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start Redis (if using): redis-server"
echo "2. Run the server: python manage.py runserver"
echo "3. If migrating from MongoDB, run: python migrate_mongodb_to_postgres.py"
echo ""
echo "Useful commands:"
echo "  - Run server: python manage.py runserver"
echo "  - Shell: python manage.py shell"
echo "  - Tests: python manage.py test"
echo "  - Create admin: python manage.py createsuperuser"
echo ""

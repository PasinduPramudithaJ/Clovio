#!/bin/bash
# Database setup script for PostgreSQL
# This script creates the database and user if they don't exist

set -e

DB_NAME="${DB_NAME:-clovio_db}"
DB_USER="${DB_USER:-clovio_user}"
DB_PASSWORD="${DB_PASSWORD:-clovio_pass}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

echo "=========================================="
echo "Clovio Database Setup"
echo "=========================================="
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST:$DB_PORT"
echo "=========================================="

# Check if PostgreSQL is accessible
echo ""
echo "Checking PostgreSQL connection..."
PGPASSWORD=postgres psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "SELECT version();" > /dev/null 2>&1 || {
    echo "ERROR: Cannot connect to PostgreSQL server"
    echo "Please ensure PostgreSQL is running and accessible"
    exit 1
}

echo "[OK] PostgreSQL server is accessible"

# Create user if it doesn't exist
echo ""
echo "Creating user '$DB_USER' if it doesn't exist..."
PGPASSWORD=postgres psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -tc "SELECT 1 FROM pg_user WHERE usename = '$DB_USER'" | grep -q 1 || \
    PGPASSWORD=postgres psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"

echo "[OK] User '$DB_USER' is ready"

# Create database if it doesn't exist
echo ""
echo "Creating database '$DB_NAME' if it doesn't exist..."
PGPASSWORD=postgres psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    PGPASSWORD=postgres psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "[OK] Database '$DB_NAME' is ready"

# Grant privileges
echo ""
echo "Granting privileges..."
PGPASSWORD=postgres psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
PGPASSWORD=postgres psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;"

echo "[OK] Privileges granted"

echo ""
echo "=========================================="
echo "Database setup complete!"
echo "=========================================="
echo ""
echo "You can now run the application with:"
echo "  python main.py"
echo "  or"
echo "  uvicorn main:app --reload"
echo ""


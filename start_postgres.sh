#!/bin/bash
# Script to start PostgreSQL for Clovio

echo "=========================================="
echo "Starting PostgreSQL Database for Clovio"
echo "=========================================="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed or not in PATH"
    echo "[INFO] Please install Docker from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^clovio_db$"; then
    echo "[INFO] Container clovio_db already exists"
    echo "[INFO] Starting existing container..."
    
    if docker start clovio_db; then
        echo "[OK] PostgreSQL container started successfully!"
        echo ""
        echo "Database is ready at: postgresql://clovio_user:clovio_pass@localhost:5432/clovio_db"
        echo ""
        echo "You can now start your backend server."
        exit 0
    else
        echo "[ERROR] Failed to start container"
        exit 1
    fi
else
    echo "[INFO] Creating new PostgreSQL container..."
    
    if docker run -d --name clovio_db \
        -e POSTGRES_USER=clovio_user \
        -e POSTGRES_PASSWORD=clovio_pass \
        -e POSTGRES_DB=clovio_db \
        -p 5432:5432 \
        postgres:15-alpine; then
        echo "[OK] PostgreSQL container created and started!"
        echo ""
        echo "Waiting for database to be ready..."
        sleep 5
        echo "[OK] Database is ready at: postgresql://clovio_user:clovio_pass@localhost:5432/clovio_db"
        echo ""
        echo "You can now start your backend server."
        exit 0
    else
        echo "[ERROR] Failed to create container"
        echo ""
        echo "Make sure Docker is installed and running."
        exit 1
    fi
fi


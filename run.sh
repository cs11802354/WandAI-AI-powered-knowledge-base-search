#!/bin/bash

# Simple startup script for Knowledge Base System

echo "Starting Knowledge Base System..."
echo ""

# Stop any existing containers
echo "Stopping any existing containers..."
docker compose down -v

# Start all services
echo "Building and starting services..."
docker compose up --build -d

# Wait for services to be ready
echo "Waiting for services to start (100 seconds)..."
sleep 100

# Check if services are healthy
echo "Checking service health..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo ""
    echo "SUCCESS! System is running."
    echo ""
    echo "Access points:"
    echo "   - API: http://localhost:8000"
    echo "   - API Docs (Swagger): http://localhost:8000/docs"
    echo "   - Celery Monitor (Flower): http://localhost:5555"
    echo ""
    echo "To test the system, run: ./test.sh"
else
    echo ""
    echo "ERROR: API is not responding."
    echo "Check logs with: docker compose logs"
fi


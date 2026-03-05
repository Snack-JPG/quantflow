#!/bin/bash

echo "Starting QuantFlow - Order Book Intelligence Platform"
echo "======================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "Building and starting services..."
docker-compose up --build

echo ""
echo "Services stopped."
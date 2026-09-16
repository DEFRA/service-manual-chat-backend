#!/bin/bash

# Exit on error
set -e

echo "Starting development environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Start dependent services
echo "Starting dependent services with Docker Compose..."
docker compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 5

# Set environment variables for local development
export PORT=8085
export AWS_ENDPOINT_URL=http://localhost:4566
export MONGO_URI=mongodb://localhost:27017/
export ENV=dev
export HOST=0.0.0.0
export LOG_CONFIG=logging-dev.json

# Load application environment variables
echo "Loading environment variables..."
if [ -f compose/aws.env ]; then
    export $(grep -v '^#' compose/aws.env | xargs)
else
    echo "Error: compose/aws.env file not found. This file is required."
    exit 1
fi

echo "Loading secrets..."
if [ -f compose/secrets.env ]; then
    export $(grep -v '^#' compose/secrets.env | xargs)
else
    echo "Error: compose/secrets.env file not found. This file is required."
    exit 1
fi

# Check uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv as per the README."
    exit 1
fi

# Start the application
echo "Starting FastAPI application..."
uv run uvicorn app.main:app --host $HOST --port $PORT --reload --log-config=$LOG_CONFIG

# Cleanup function
cleanup() {
    echo "Shutting down..."
    echo "Development server stopped."
}

# Register cleanup function
trap cleanup EXIT

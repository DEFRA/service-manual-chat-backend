#!/bin/bash

# Exit on error
set -e

echo "Starting development environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again." >&2
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
# Bedrock is the one AWS service that must reach AWS itself, not localstack.
export AWS_ENDPOINT_URL_BEDROCK_RUNTIME=https://bedrock-runtime.${BEDROCK_REGION:-eu-west-2}.amazonaws.com
# The toolkit pages and the prompt, as compose mounts them.
export CONTENT_DIR=${CONTENT_DIR:-../service-manual-ui/src/content}
export PYDANTIC_AI_NO_BANNER=1
export MONGO_URI=mongodb://localhost:27017/
export ENV=dev
export HOST=0.0.0.0
export LOG_CONFIG=logging-dev.json

# Load application environment variables
echo "Loading environment variables..."
if [[ -f compose/aws.env ]]; then
    export $(grep -v '^#' compose/aws.env | xargs)
else
    echo "Error: compose/aws.env file not found. This file is required." >&2
    exit 1
fi

echo "Loading secrets..."
if [[ -f compose/secrets.env ]]; then
    export $(grep -v '^#' compose/secrets.env | xargs)
else
    echo "Error: compose/secrets.env file not found. This file is required." >&2
    exit 1
fi

# Check uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv as per the README." >&2
    exit 1
fi

# Start the application
echo "Starting FastAPI application..."
# --no-build is not an option: pymongo has no wheel for this Python yet.
uv run uvicorn app.main:app --host $HOST --port $PORT --reload --log-config=$LOG_CONFIG # NOSONAR

# Cleanup function
cleanup() {
    echo "Shutting down..."
    echo "Development server stopped."
}

# Register cleanup function
trap cleanup EXIT

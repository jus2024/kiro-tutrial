#!/bin/bash
# Build script for AI要約API

set -e

echo "Building AI要約API..."

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run tests
echo "Running tests..."
pytest tests/unit/ -v

# Build SAM application
echo "Building SAM application..."
sam build

echo "Build completed successfully!"

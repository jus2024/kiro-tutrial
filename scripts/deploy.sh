#!/bin/bash
# Deployment script for AI要約API

set -e

ENVIRONMENT=${1:-dev}

echo "Deploying AI要約API to environment: $ENVIRONMENT"

# Build first
./scripts/build.sh

# Deploy
echo "Deploying to AWS..."
sam deploy --parameter-overrides Environment=$ENVIRONMENT

echo "Deployment completed successfully!"
echo "Check AWS CloudFormation console for stack outputs"

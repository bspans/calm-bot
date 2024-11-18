#!/bin/bash
set -e

# Build frontend
echo "Building frontend..."
cd next-app
npm install
npm run build

# Build and deploy CDK
echo "Building and deploying CDK..."
cd ../cdk-app
npm install
npm run build
cdk deploy

echo "Deployment complete!"

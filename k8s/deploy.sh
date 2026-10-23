#!/bin/bash
# Fast API Micro - Kubernetes Deployment Script
# This script deploys all services to Kubernetes

set -e  # Exit on error

NAMESPACE="fast-api-micro"

echo "=== Fast API Micro - Kubernetes Deployment ==="

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed. Install it from https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Create namespace
echo "[1/4] Creating namespace '$NAMESPACE'..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Check if RabbitMQ is already running locally
if [ -n "$(docker ps -aq --filter 'name=rabbitmq')" ]; then
    echo "[2/4] RabbitMQ detected in Docker. For local Kubernetes testing, either:"
    echo "  - Stop the local RabbitMQ container"
    echo "  - Set RABBITMQ_URL in environment to the Docker IP (e.g., amqp://user:password@localhost:5672/)"
    echo ""
    read -p "Press Enter to continue with deployment..."
fi

# Apply all manifests
echo "[3/4] Deploying all services..."
kubectl apply -f deploy-all.yaml

echo ""
echo "[4/4] Verifying deployments..."
kubectl get pods -n "$NAMESPACE" --watch

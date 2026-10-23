# Fast API Micro - Kubernetes Setup Guide

## Overview

This microservices architecture consists of 7 services:
- **auth-service** (8000) - Authentication
- **api-service/post-service** (8082) - Main API
- **chat-service** (8083) - Chat functionality
- **marketplace-service** (8084) - Marketplace features
- **notification-service** (8085) - Email notifications
- **upload-service** (8086) - File uploads
- **worker** - RabbitMQ message consumer

## Prerequisites

1. **Kubernetes Cluster** (Minikube, Kind, EKS, GKE, etc.)
2. **kubectl** installed
3. **Helm** (optional, for ingress controller)

```bash
# Install kubectl if needed
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Verify installation
kubectl version --client
```

## Quick Start (Local Development)

### Option 1: Using Minikube

```bash
# Start Minikube with necessary ports
minikube start \
  --memory=4096 \
  --cpus=4 \
  --insecure-skip-tls-verify

# Deploy all services
kubectl apply -f k8s/
```

### Option 2: Using Kind (Recommended)

```bash
# Create cluster
kind create cluster --name fast-api-micro

# Deploy
kubectl apply -f k8s/
```

### Apply only RabbitMQ and Services
```bash
# Just the application services
kubectl apply -f k8s/deploy-all.yaml

# Or just RabbitMQ
kubectl apply -f k8s/rabbitmq.yaml
```

## Local Development with Docker + Kubernetes Manifests

If you have a local Docker network matching the expected ports, create these environment overrides:

### auth_service/.env.local (or modify .env):
```env
DATABASE_URL=postgresql://user:secret@localhost:5432/auth_service?sslmode=disable
RABBITMQ_URL=amqp://user:password@localhost:5672/
```

### api_service/.env.local:
```env
DATABASE_URL=postgresql://user:secret@localhost:5432/post_db?sslmode=disable
AUTH_VALIDATOR=http://localhost:8000/api/auth/verify_authentication
```

### chat_service/.env.local:
```env
DATABASE_URL=postgresql://user:secret@localhost:5432/chat_db?sslmode=disable
AUTH_VALIDATOR=http://localhost:8000/api/auth/verify_authentication
```

And so on for other services...

## Complete Deployment Command

```bash
# Apply all manifests at once
kubectl apply -f k8s/

# Or apply step by step
kubectl apply -f k8s/rabbitmq.yaml      # Message broker
kubectl apply -f k8s/deploy-all.yaml     # All services
```

## Verify Deployment

```bash
# List namespaces
kubectl get ns | grep fast-api-micro

# List all resources in namespace
kubectl get all -n fast-api-micro

# Check pods
kubectl get pods -n fast-api-micro

# View logs
kubectl logs -f deployment/auth-service -n fast-api-micro
kubectl logs -f deployment/worker -n fast-api-micro

# Describe pods for details
kubectl describe pod -n fast-api-micro | grep -E "Pod|State|Container"
```

## Service Endpoints

```bash
# Get service IPs
kubectl get svc -n fast-api-micro

# Access services from outside cluster (if needed)
minikube service auth-service --url           # Minikube
kind get ip --name fast-api-micro             # Kind + port forwarding
```

## Ingress Setup

The `ingress.yaml` requires an Ingress Controller. For local development:

### With Minikube + NGINX Ingress:
```bash
minikube addon enable ingress-dns
kubectl apply -f k8s/ingress.yaml

# Access via localhost
curl http://localhost/api/auth/...
```

## Environment Variables Reference

All services share these environment variables (from ConfigMap):

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `SECRET_KEY` | Secret key for JWT tokens | `d2bcbac0d9e7f5ffaf6b0fd44d8042f7fd438d7b24ec5e2f31e3c74a6233bcf9` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `30` |

### Service-specific variables:

**auth_service:**
- `DATABASE_URL`: `postgresql://user:secret@<DB_HOST>:5432/auth_service?sslmode=disable`

**post_service:**
- `DATABASE_URL`: `postgresql://user:secret@<DB_HOST>:5432/post_db?sslmode=disable`
- `AUTH_VALIDATOR`: `http://auth-service:8000/api/auth/verify_authentication`

**chat_service:**
- `DATABASE_URL`: `postgresql://user:secret@<DB_HOST>:5432/chat_db?sslmode=disable`
- `AUTH_VALIDATOR`: `http://auth-service:8000/api/auth/verify_authentication`

**marketplace_service:**
- `DATABASE_URL`: `postgresql://user:secret@<DB_HOST>:5432/marketplace_db?sslmode=disable`
- `AUTH_VALIDATOR`: `http://auth-service:8000/api/auth/verify_authentication`

**notification_service:**
- `DATABASE_URL`: `postgresql://user:secret@<DB_HOST>:5432/notification_db?sslmode=disable`
- `RABBITMQ_URL`: `amqp://user:password@rabbitmq:5672/`
- `AUTH_VALIDATOR`: `http://auth-service:8000/api/auth/verify_authentication`

**upload_service:**
- `DATABASE_URL`: `postgresql://user:secret@<DB_HOST>:5432/upload_db?sslmode=disable`
- `BASE_URL`: `http://upload-service:8086` (for file serving)
- `AUTH_VALIDATOR`: `http://auth-service:8000/api/auth/verify_authentication`

## Troubleshooting

### Port Conflicts
```bash
# Check if ports are in use
lsof -i :5672  # RabbitMQ
lsof -i :15672 # RabbitMQ management UI
lsof -i :8000  # auth-service
```

### Service Discovery Issues
Ensure proper DNS resolution:
```bash
kubectl run -it --rm debug --image=busybox --command -- nslookup <service-name>
```

### Pod Stuck in Pending State
```bash
kubectl describe pod -n fast-api-micro | grep Events
# Check resource quotas
kubectl get quota -n fast-api-micro
```

### RabbitMQ Connection Issues
Verify RabbitMQ is running:
```bash
kubectl get pods -n fast-api-micro | grep rabbitmq
kubectl logs deployment/rabbitmq -n fast-api-micro --tail=100
# Try connecting directly
kubectl exec -it <rabbitmq-pod> -- rabbitmqctl list_vhosts
```

## Database Setup

Currently, the services expect external PostgreSQL databases. For local development:

### Option 1: Use External Docker DBs
```bash
docker run -d --name postgres-auth -p 5433:5432 -e POSTGRES_USER=user -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=auth_service postgres:15
docker run -d --name postgres-api -p 5434:5432 -e POSTGRES_USER=user -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=post_db postgres:15
# ... create more DB containers for each service
```

### Option 2: Use PostgreSQL Operator
Install the Postgres operator in Kubernetes and deploy databases.

## Scaling

To scale any service:
```bash
kubectl scale deployment <service-name> --replicas=3 -n fast-api-micro
```

## Cleanup

```bash
# Remove namespace (removes all resources)
kubectl delete ns fast-api-micro

# Or remove specific resource
kubectl delete deployment/<name> -n fast-api-micro
```

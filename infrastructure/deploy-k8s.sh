#!/usr/bin/env bash
# ====================================================================
# deploy-k8s.sh - FASE 5: Script de Deployment Kubernetes
# Deploy completo do sistema Engenharia CAD em Kubernetes
# ====================================================================

set -e

echo "?? Iniciando deployment Kubernetes - Engenharia CAD"

# Verificar kubectl
if ! command -v kubectl &> /dev/null; then
    echo "? kubectl não encontrado. Instale o kubectl primeiro."
    exit 1
fi

# Verificar conexão com cluster
echo "?? Verificando conexão com cluster Kubernetes..."
kubectl cluster-info

# Criar namespace
echo "?? Criando namespace Engenharia CAD..."
kubectl apply -f k8s-deployment.yml

# Aguardar namespace
kubectl wait --for=condition=ready pod --all -n Engenharia CAD --timeout=60s || true

# Build das imagens (assumindo Docker)
echo "???  Building imagens Docker..."

# CPU Worker
echo "Building celery-worker..."
docker build -f Dockerfile.celery -t Engenharia CAD/celery-worker:latest .

# GPU Worker
echo "Building celery-worker-gpu..."
docker build -f Dockerfile.celery.gpu -t Engenharia CAD/celery-worker-gpu:latest .

# API Server
echo "Building api-server..."
docker build -f Dockerfile.api -t Engenharia CAD/api-server:latest .

# Push para registry (opcional - descomente se necessário)
# echo "Pushing images..."
# docker push Engenharia CAD/celery-worker:latest
# docker push Engenharia CAD/celery-worker-gpu:latest
# docker push Engenharia CAD/api-server:latest

# Deploy dos componentes
echo "?? Deploying componentes..."

# Redis
echo "Deploying Redis..."
kubectl apply -f k8s-deployment.yml
kubectl wait --for=condition=available --timeout=300s deployment/redis -n Engenharia CAD

# RabbitMQ
echo "Deploying RabbitMQ..."
kubectl wait --for=condition=available --timeout=300s deployment/rabbitmq -n Engenharia CAD

# PostgreSQL
echo "Deploying PostgreSQL..."
kubectl wait --for=condition=available --timeout=300s deployment/postgres -n Engenharia CAD

# Workers CPU
echo "Deploying CPU Workers..."
kubectl wait --for=condition=available --timeout=300s deployment/celery-worker-cpu -n Engenharia CAD

# Workers GPU (se GPU disponível)
if kubectl get nodes -o json | jq -e '.items[].status.capacity."nvidia.com/gpu"' &>/dev/null; then
    echo "?? GPU detectada - Deploying GPU Workers..."
    kubectl wait --for=condition=available --timeout=300s deployment/celery-worker-gpu -n Engenharia CAD
else
    echo "??  GPU não detectada - Pulando GPU workers"
fi

# API Server
echo "Deploying API Server..."
kubectl wait --for=condition=available --timeout=300s deployment/api-server -n Engenharia CAD

# Services
echo "Creating Services..."
kubectl apply -f k8s-deployment.yml

# Aguardar todos os pods ficarem ready
echo "? Aguardando todos os pods ficarem ready..."
kubectl wait --for=condition=ready pod --all -n Engenharia CAD --timeout=600s

# Status final
echo ""
echo "? Deployment concluído!"
echo ""
echo "?? Status dos componentes:"
kubectl get pods -n Engenharia CAD
echo ""
echo "?? Services disponíveis:"
kubectl get services -n Engenharia CAD
echo ""
echo "?? URLs de acesso:"
echo "  API Server: http://$(kubectl get service api-service -n Engenharia CAD -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):8000"
echo "  RabbitMQ Management: http://$(kubectl get service rabbitmq-service -n Engenharia CAD -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):15672"
echo "  Grafana: http://$(kubectl get service grafana-service -n Engenharia CAD -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):3000"
echo ""
echo "?? Comandos úteis:"
echo "  Ver logs: kubectl logs -f deployment/api-server -n Engenharia CAD"
echo "  Scaling: kubectl scale deployment celery-worker-cpu --replicas=5 -n Engenharia CAD"
echo "  Status: kubectl get all -n Engenharia CAD"

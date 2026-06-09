#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Neurex Platform Infrastructure Deployment Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage: ./deploy-infrastructure.sh [dev|staging|prod]
# Example: ./deploy-infrastructure.sh prod
#

set -euo pipefail

ENVIRONMENT="${1:-dev}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
INFRA_DIR="$ROOT_DIR/infra"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# ────────────────────────────────────────────────────────────────────────────
# Validation
# ────────────────────────────────────────────────────────────────────────────

validate_environment() {
    if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
        log_error "Invalid environment: $ENVIRONMENT"
        echo "Usage: $0 [dev|staging|prod]"
        exit 1
    fi
    log_info "Deploying to environment: $ENVIRONMENT"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    log_success "kubectl found: $(kubectl version --short --client)"

    # Check helm
    if ! command -v helm &> /dev/null; then
        log_error "helm not found. Please install helm."
        exit 1
    fi
    log_success "helm found: $(helm version --short)"

    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    log_success "Connected to cluster: $(kubectl config current-context)"

    # Check storage classes
    if ! kubectl get storageclass &> /dev/null; then
        log_error "No storage classes found. Please configure storage."
        exit 1
    fi
    log_success "Storage classes available"
}

# ────────────────────────────────────────────────────────────────────────────
# Namespace & Secrets Setup
# ────────────────────────────────────────────────────────────────────────────

setup_namespace() {
    log_info "Setting up namespace..."

    if kubectl get namespace neurex &> /dev/null; then
        log_warning "Namespace 'neurex' already exists"
    else
        kubectl create namespace neurex
        kubectl label namespace neurex environment=$ENVIRONMENT
        log_success "Namespace 'neurex' created"
    fi
}

setup_secrets() {
    log_info "Setting up secrets..."

    if kubectl get secret neurex-secrets -n neurex &> /dev/null; then
        log_warning "Secret 'neurex-secrets' already exists. Skipping..."
        return
    fi

    # Generate secrets
    JWT_SECRET=$(openssl rand -base64 64)
    ENGINE_INTERNAL_KEY=$(openssl rand -hex 32)
    DB_PASSWORD="${DB_PASSWORD:-changeme}"

    # Determine database URL
    case $ENVIRONMENT in
        prod)
            DB_HOST="postgres.neurex.svc.cluster.local"
            DB_URL="postgresql://neurex:$DB_PASSWORD@$DB_HOST:5432/neurex_prod"
            ;;
        staging)
            DB_HOST="postgres.neurex.svc.cluster.local"
            DB_URL="postgresql://neurex:$DB_PASSWORD@$DB_HOST:5432/neurex_staging"
            ;;
        *)
            DB_HOST="postgres.neurex.svc.cluster.local"
            DB_URL="postgresql://neurex:$DB_PASSWORD@$DB_HOST:5432/neurex_dev"
            ;;
    esac

    kubectl create secret generic neurex-secrets \
        --from-literal=database-url="$DB_URL" \
        --from-literal=jwt-secret="$JWT_SECRET" \
        --from-literal=engine-internal-key="$ENGINE_INTERNAL_KEY" \
        -n neurex

    log_success "Secrets created"
    log_warning "Save these values securely:"
    echo "  Database URL: $DB_URL"
    echo "  JWT Secret: $JWT_SECRET"
    echo "  Engine Key: $ENGINE_INTERNAL_KEY"
}

# ────────────────────────────────────────────────────────────────────────────
# Helm Repository Setup
# ────────────────────────────────────────────────────────────────────────────

setup_helm_repos() {
    log_info "Setting up Helm repositories..."

    # Bitnami charts
    helm repo add bitnami https://charts.bitnami.com/bitnami || true

    # Prometheus community
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts || true

    # Grafana
    helm repo add grafana https://grafana.github.io/helm-charts || true

    # ArgoCD
    helm repo add argo https://argoproj.github.io/argo-helm || true

    helm repo update
    log_success "Helm repositories updated"
}

# ────────────────────────────────────────────────────────────────────────────
# Core Infrastructure Deployment
# ────────────────────────────────────────────────────────────────────────────

deploy_helm_chart() {
    log_info "Deploying Neurex platform via Helm..."

    local values_file="$INFRA_DIR/helm/neurex-platform/values-${ENVIRONMENT}.yaml"
    local base_values="$INFRA_DIR/helm/neurex-platform/values.yaml"

    if [[ ! -f "$values_file" ]]; then
        log_warning "Values file not found: $values_file"
        log_info "Using base values: $base_values"
        values_file="$base_values"
    fi

    # Update Helm dependencies
    helm dependency update "$INFRA_DIR/helm/neurex-platform"

    # Dry-run first
    log_info "Running Helm template validation..."
    helm template neurex "$INFRA_DIR/helm/neurex-platform" \
        -f "$values_file" \
        -n neurex > /tmp/neurex-manifest.yaml

    if helm install neurex "$INFRA_DIR/helm/neurex-platform" \
        -f "$values_file" \
        -n neurex \
        --create-namespace \
        --wait \
        --timeout 10m 2>/dev/null; then
        log_success "Helm chart deployed successfully"
    else
        log_warning "Helm chart already installed, upgrading instead..."
        helm upgrade neurex "$INFRA_DIR/helm/neurex-platform" \
            -f "$values_file" \
            -n neurex \
            --wait \
            --timeout 10m
        log_success "Helm chart upgraded successfully"
    fi
}

# ────────────────────────────────────────────────────────────────────────────
# Monitoring Stack Deployment
# ────────────────────────────────────────────────────────────────────────────

deploy_monitoring() {
    log_info "Deploying monitoring stack..."

    # Create monitoring namespace
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

    # Deploy Prometheus
    log_info "Deploying Prometheus..."
    helm install prometheus prometheus-community/kube-prometheus-stack \
        -n monitoring \
        --set prometheus.prometheusSpec.retention=15d \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
        --wait --timeout 5m 2>/dev/null || \
    helm upgrade prometheus prometheus-community/kube-prometheus-stack \
        -n monitoring \
        --set prometheus.prometheusSpec.retention=15d \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
        --wait --timeout 5m

    log_success "Prometheus deployed"

    # Apply alert rules
    log_info "Applying Prometheus alert rules..."
    kubectl apply -f "$INFRA_DIR/k8s/prometheus-rules.yaml"
    log_success "Alert rules applied"
}

# ────────────────────────────────────────────────────────────────────────────
# Logging Stack Deployment
# ────────────────────────────────────────────────────────────────────────────

deploy_logging() {
    log_info "Deploying logging stack (Loki)..."

    # Create logging namespace
    kubectl create namespace logging --dry-run=client -o yaml | kubectl apply -f -

    # Deploy Loki
    helm install loki grafana/loki-stack \
        -n logging \
        --set promtail.enabled=true \
        --set grafana.enabled=false \
        --wait --timeout 5m 2>/dev/null || \
    helm upgrade loki grafana/loki-stack \
        -n logging \
        --set promtail.enabled=true \
        --set grafana.enabled=false \
        --wait --timeout 5m

    log_success "Loki logging stack deployed"
}

# ────────────────────────────────────────────────────────────────────────────
# ArgoCD Setup (Optional)
# ────────────────────────────────────────────────────────────────────────────

deploy_argocd() {
    log_info "Deploying ArgoCD (optional)..."

    # Create argocd namespace
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

    # Deploy ArgoCD
    helm install argocd argo/argo-cd \
        -n argocd \
        --set server.insecure=true \
        --wait --timeout 5m 2>/dev/null || \
    helm upgrade argocd argo/argo-cd \
        -n argocd \
        --set server.insecure=true \
        --wait --timeout 5m

    log_success "ArgoCD deployed"

    # Apply Neurex application
    log_info "Registering Neurex application with ArgoCD..."
    kubectl apply -f "$INFRA_DIR/argocd/neurex-application.yaml"
    log_success "ArgoCD application registered"
}

# ────────────────────────────────────────────────────────────────────────────
# Post-Deployment Verification
# ────────────────────────────────────────────────────────────────────────────

verify_deployment() {
    log_info "Verifying deployment..."

    # Check core deployments
    log_info "Checking core services..."
    kubectl get deployments -n neurex
    kubectl get services -n neurex
    kubectl get pods -n neurex

    # Wait for pods to be ready
    log_info "Waiting for pods to be ready (max 5 minutes)..."
    kubectl wait --for=condition=ready pod \
        -l app in (neurex-backend,neurex-frontend,neurex-engine) \
        -n neurex \
        --timeout=300s || log_warning "Some pods not ready yet"

    # Get pod summary
    log_info "Pod status summary:"
    kubectl get pods -n neurex --no-headers | awk '{print $3}' | sort | uniq -c

    # Check ingress
    log_info "Checking Ingress..."
    kubectl get ingress -n neurex

    log_success "Deployment verification complete"
}

# ────────────────────────────────────────────────────────────────────────────
# Access Information
# ────────────────────────────────────────────────────────────────────────────

print_access_info() {
    log_info "Access Information:"
    echo ""
    echo "Neurex Platform:"
    echo "  URL: https://bgtest.dev (after DNS configuration)"
    echo "  Namespace: neurex"
    echo "  Helm Release: neurex"
    echo ""
    echo "Monitoring:"
    echo "  Prometheus: kubectl port-forward svc/prometheus-operated -n monitoring 9090:9090"
    echo "  Grafana: kubectl port-forward svc/grafana -n monitoring 3000:3000"
    echo "  URL: http://localhost:3000"
    echo ""
    echo "Logging:"
    echo "  Loki: kubectl port-forward svc/loki -n logging 3100:3100"
    echo ""
    if kubectl get deployment -n argocd argocd-server &> /dev/null; then
        echo "GitOps (ArgoCD):"
        echo "  kubectl port-forward svc/argocd-server -n argocd 8080:443"
        ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
        echo "  Initial password: $ARGOCD_PASSWORD"
        echo "  URL: https://localhost:8080"
        echo ""
    fi
    echo "To check pod status:"
    echo "  kubectl get pods -n neurex -w"
    echo ""
    echo "To view logs:"
    echo "  kubectl logs -f deployment/neurex-backend -n neurex"
    echo ""
}

# ────────────────────────────────────────────────────────────────────────────
# Main Execution
# ────────────────────────────────────────────────────────────────────────────

main() {
    echo "╔════════════════════════════════════════════════════════════════════════════════╗"
    echo "║           Neurex Platform Infrastructure Deployment                            ║"
    echo "╚════════════════════════════════════════════════════════════════════════════════╝"
    echo ""

    validate_environment
    check_prerequisites
    setup_namespace
    setup_secrets
    setup_helm_repos
    deploy_helm_chart
    deploy_monitoring
    deploy_logging

    # Optional: ArgoCD
    if [[ "$ENVIRONMENT" == "prod" ]]; then
        read -p "Deploy ArgoCD for GitOps? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            deploy_argocd
        fi
    fi

    verify_deployment
    print_access_info

    log_success "Infrastructure deployment complete!"
    log_info "Next steps:"
    echo "  1. Configure DNS: bgtest.dev → Load Balancer IP"
    echo "  2. Update TLS certificates: cert-manager will auto-provision"
    echo "  3. Test application: https://bgtest.dev"
    echo "  4. Monitor dashboards: Prometheus & Grafana"
}

# Run main function
main "$@"

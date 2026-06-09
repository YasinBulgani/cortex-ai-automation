#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Neurex Platform Scaling & Performance Guide
# ═══════════════════════════════════════════════════════════════════════════════
#
# This script provides utilities for monitoring, scaling, and optimizing
# the Neurex platform deployment.
#
# Usage: ./scaling-guide.sh [command] [args]
# Commands:
#   monitor              - Real-time resource monitoring
#   scale <component>    - Manual scaling
#   hpa-status          - HPA status and metrics
#   optimize            - Optimization recommendations
#   bottleneck          - Find performance bottlenecks
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMMAND="${1:-help}"
NAMESPACE="neurex"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

# ────────────────────────────────────────────────────────────────────────────
# Monitoring Functions
# ────────────────────────────────────────────────────────────────────────────

monitor_resources() {
    log_info "Real-time resource monitoring (Press Ctrl+C to stop)..."
    echo ""
    echo "Nodes:"
    kubectl top nodes

    echo ""
    echo "Pods by CPU:"
    kubectl top pods -n $NAMESPACE --sort-by=cpu

    echo ""
    echo "Pods by Memory:"
    kubectl top pods -n $NAMESPACE --sort-by=memory

    # Watch mode
    watch -n 2 "echo 'Nodes:'; kubectl top nodes; echo ''; echo 'Pods:'; kubectl top pods -n $NAMESPACE | head -10"
}

# ────────────────────────────────────────────────────────────────────────────
# Manual Scaling Functions
# ────────────────────────────────────────────────────────────────────────────

scale_backend() {
    local replicas="${1:-3}"
    log_info "Scaling neurex-backend to $replicas replicas..."
    kubectl scale deployment neurex-backend --replicas=$replicas -n $NAMESPACE
    log_success "Scaled successfully"
    kubectl rollout status deployment/neurex-backend -n $NAMESPACE
}

scale_frontend() {
    local replicas="${1:-3}"
    log_info "Scaling neurex-frontend to $replicas replicas..."
    kubectl scale deployment neurex-frontend --replicas=$replicas -n $NAMESPACE
    log_success "Scaled successfully"
    kubectl rollout status deployment/neurex-frontend -n $NAMESPACE
}

scale_ai_gateway() {
    local replicas="${1:-4}"
    log_info "Scaling neurex-ai-gateway to $replicas replicas..."
    kubectl scale deployment neurex-ai-gateway --replicas=$replicas -n $NAMESPACE
    log_success "Scaled successfully"
    kubectl rollout status deployment/neurex-ai-gateway -n $NAMESPACE
}

scale_component() {
    local component="$1"
    local replicas="${2:-3}"

    case "$component" in
        backend)
            scale_backend "$replicas"
            ;;
        frontend)
            scale_frontend "$replicas"
            ;;
        ai-gateway)
            scale_ai_gateway "$replicas"
            ;;
        *)
            log_warning "Unknown component: $component"
            echo "Available: backend, frontend, ai-gateway"
            return 1
            ;;
    esac
}

# ────────────────────────────────────────────────────────────────────────────
# HPA Status & Metrics
# ────────────────────────────────────────────────────────────────────────────

hpa_status() {
    log_info "HPA Status:"
    kubectl get hpa -n $NAMESPACE -o wide

    echo ""
    log_info "Backend HPA Details:"
    kubectl describe hpa neurex-backend-hpa -n $NAMESPACE 2>/dev/null || echo "Not found"

    echo ""
    log_info "AI Gateway HPA Details:"
    kubectl describe hpa neurex-ai-gateway-hpa -n $NAMESPACE 2>/dev/null || echo "Not found"

    echo ""
    log_info "Current Metrics (Prometheus):"
    # Query Prometheus for current CPU/memory
    echo "Backend CPU utilization:"
    kubectl exec -n monitoring prometheus-operated-0 -- \
        promtool query instant 'avg(rate(container_cpu_usage_seconds_total{pod=~"neurex-backend.*"}[5m]))' 2>/dev/null || echo "N/A"
}

# ────────────────────────────────────────────────────────────────────────────
# Performance Optimization Recommendations
# ────────────────────────────────────────────────────────────────────────────

optimization_recommendations() {
    log_info "Analyzing performance metrics..."
    echo ""

    # Check resource requests vs actual usage
    echo "Resource Utilization Analysis:"
    kubectl get pods -n $NAMESPACE -o json | jq -r '.items[] |
        select(.status.conditions[]? | select(.type=="Ready" and .status=="True")) |
        {
            name: .metadata.name,
            cpu_request: .spec.containers[0].resources.requests.cpu,
            memory_request: .spec.containers[0].resources.requests.memory,
            actual_cpu: (.status.containerStatuses[0].restartCount? | "high-restart"),
            phase: .status.phase
        }' | column -t

    echo ""
    log_info "Recommendations:"

    # Check for OOM kills
    local oom_count=$(kubectl get pods -n $NAMESPACE -o json | jq '[.items[].status.containerStatuses[]? | select(.lastState.terminated?.reason=="OOMKilled")] | length')
    if [ "$oom_count" -gt 0 ]; then
        log_warning "Found $oom_count pods with OOMKilled events"
        echo "  → Increase memory limits or scale horizontally"
    fi

    # Check for restarts
    local restart_count=$(kubectl get pods -n $NAMESPACE -o json | jq '[.items[].status.containerStatuses[]? | select(.restartCount > 3)] | length')
    if [ "$restart_count" -gt 0 ]; then
        log_warning "Found $restart_count pods with >3 restarts"
        echo "  → Check pod logs for errors: kubectl logs <pod> -n $NAMESPACE"
    fi

    # Check for pending pods
    local pending=$(kubectl get pods -n $NAMESPACE --field-selector=status.phase=Pending -o name | wc -l)
    if [ "$pending" -gt 0 ]; then
        log_warning "Found $pending pending pods"
        echo "  → Check node capacity or resource constraints"
        echo "  → Run: kubectl describe nodes"
    fi

    echo ""
    echo "Storage Optimization:"
    kubectl get pvc -n $NAMESPACE -o wide

    echo ""
    log_info "Common Issues & Solutions:"
    echo "  1. High Memory Usage?"
    echo "     - Run: kubectl top pods -n $NAMESPACE --sort-by=memory"
    echo "     - Check for memory leaks in application logs"
    echo "     - Increase memory limits if needed"
    echo ""
    echo "  2. High CPU Usage?"
    echo "     - Run: kubectl top pods -n $NAMESPACE --sort-by=cpu"
    echo "     - Profile application with pprof/py-spy"
    echo "     - Consider vertical scaling (increase resources)"
    echo ""
    echo "  3. Database Bottleneck?"
    echo "     - Check connection pool: kubectl exec -it <backend-pod> -- psql"
    echo "     - Monitor slow queries in PostgreSQL logs"
    echo "     - Add database indexes if needed"
    echo ""
    echo "  4. API Latency?"
    echo "     - Check Prometheus: histogram_quantile(0.95, http_request_duration_seconds)"
    echo "     - Check backend logs for slow endpoints"
    echo "     - Consider caching for frequently accessed data"
}

# ────────────────────────────────────────────────────────────────────────────
# Bottleneck Analysis
# ────────────────────────────────────────────────────────────────────────────

find_bottlenecks() {
    log_info "Analyzing system for bottlenecks..."
    echo ""

    # 1. Database performance
    echo "📊 Database Analysis:"
    echo "  Checking PostgreSQL stats..."
    kubectl exec -n $NAMESPACE $(kubectl get pod -n $NAMESPACE -l app=neurex-backend -o name | head -1) -- \
        psql -h postgres -U neurex -d neurex_prod -c \
        "SELECT schemaname, tablename, round(pg_total_relation_size(schemaname||'.'||tablename)/1024/1024,2) as size_mb
         FROM pg_tables WHERE schemaname != 'pg_catalog' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;" 2>/dev/null || echo "  N/A"

    echo ""
    echo "🔄 Queue/Processing Latency:"
    echo "  Checking test engine queue..."
    kubectl logs -n $NAMESPACE -l app=neurex-engine --tail=50 | grep -i "queue\|latency" || echo "  No queue info found"

    echo ""
    echo "🔌 Connection Pool Status:"
    kubectl exec -n $NAMESPACE $(kubectl get pod -n $NAMESPACE -l app=neurex-backend -o name | head -1) -- \
        sh -c 'curl -s localhost:8000/metrics | grep -E "sqlalchemy|connection"' 2>/dev/null || echo "  Metrics not available"

    echo ""
    echo "📡 Network I/O:"
    kubectl top nodes --containers=true | grep -E "neurex|Total"

    echo ""
    echo "💾 Storage Performance:"
    kubectl exec -n $NAMESPACE $(kubectl get pod -n $NAMESPACE -l app=neurex-engine -o name | head -1) -- \
        sh -c 'df -h /app' 2>/dev/null || echo "  N/A"

    echo ""
    log_info "Common Bottlenecks & Solutions:"
    echo "  1. Database Lock Contention"
    echo "     SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC;"
    echo ""
    echo "  2. Slow API Endpoints"
    echo "     Check Prometheus: topk(5, rate(http_request_duration_seconds_sum[5m]))"
    echo ""
    echo "  3. Memory Pressure"
    echo "     Check available memory: free -m"
    echo "     Configure pod memory limits based on actual usage"
    echo ""
    echo "  4. Disk I/O Saturation"
    echo "     Monitor iostat or AWS CloudWatch"
    echo "     Consider faster storage (SSD) or optimization"
}

# ────────────────────────────────────────────────────────────────────────────
# Scaling Decision Matrix
# ────────────────────────────────────────────────────────────────────────────

scaling_decisions() {
    log_info "Scaling Decision Matrix:"
    echo ""
    cat << 'EOF'
Metric                  | Threshold | Action
─────────────────────────────────────────────────────────────────────────────
CPU Usage               | > 70%     | Scale up (HPA handles automatically)
Memory Usage            | > 80%     | Increase pod memory limit or scale up
API P95 Latency         | > 1s      | Scale up backends or optimize queries
Error Rate (5xx)        | > 5%      | Check logs, may need more capacity
Database Connections    | > 80%     | Increase pool size or scale down clients
Queue Depth (Engine)    | > 100     | Scale up engine workers
Disk Usage              | > 85%     | Clean old data or expand storage
Node CPU Available      | < 20%     | Add more nodes or optimize pods

EOF

    echo ""
    echo "Recommended Scaling Strategy:"
    echo "─────────────────────────────────────────────────────────────────────────────"
    echo ""
    echo "1. HORIZONTAL SCALING (Add More Pods)"
    echo "   When: CPU bound, handling more requests"
    echo "   How:  HPA automatically scales 2-6 replicas based on CPU/memory"
    echo "   Manual: kubectl scale deployment neurex-backend --replicas=5 -n neurex"
    echo ""
    echo "2. VERTICAL SCALING (Increase Resource Limits)"
    echo "   When: Memory bound, complex queries"
    echo "   How:  Update deployment resource limits"
    echo "   Example: kubectl set resources deployment/neurex-backend \\"
    echo "            --limits=cpu=2000m,memory=2Gi -n neurex"
    echo ""
    echo "3. CLUSTER SCALING (Add Nodes)"
    echo "   When: All resources exhausted, pods pending"
    echo "   How:  Auto-scaling groups or manual node provisioning"
    echo "   Check: kubectl top nodes (should have >20% available)"
    echo ""
}

# ────────────────────────────────────────────────────────────────────────────
# Help & Documentation
# ────────────────────────────────────────────────────────────────────────────

print_help() {
    cat << 'EOF'
╔════════════════════════════════════════════════════════════════════════════════╗
║      Neurex Platform Scaling & Performance Guide                              ║
╚════════════════════════════════════════════════════════════════════════════════╝

USAGE:
    ./scaling-guide.sh [command] [args]

COMMANDS:

    monitor
        Show real-time resource monitoring (CPU, memory by pod)
        Example: ./scaling-guide.sh monitor

    scale <component> [replicas]
        Manually scale a component to N replicas
        Components: backend, frontend, ai-gateway
        Example: ./scaling-guide.sh scale backend 5

    hpa-status
        Show HPA (Horizontal Pod Autoscaler) status and metrics
        Example: ./scaling-guide.sh hpa-status

    optimize
        Analyze current metrics and provide optimization recommendations
        Example: ./scaling-guide.sh optimize

    bottleneck
        Identify performance bottlenecks in database, API, storage
        Example: ./scaling-guide.sh bottleneck

    decisions
        Display scaling decision matrix and strategy
        Example: ./scaling-guide.sh decisions

    help
        Show this help message
        Example: ./scaling-guide.sh help

QUICK START:

1. Monitor Resources:
   ./scaling-guide.sh monitor

2. Check HPA Status:
   ./scaling-guide.sh hpa-status

3. Find Bottlenecks:
   ./scaling-guide.sh bottleneck

4. Get Recommendations:
   ./scaling-guide.sh optimize

5. Scale Manually if Needed:
   ./scaling-guide.sh scale backend 5

COMMON SCENARIOS:

Scenario: High API latency
  1. ./scaling-guide.sh bottleneck     # Find source
  2. ./scaling-guide.sh scale backend 5  # Scale up
  3. Monitor: watch -n 2 'kubectl top pods -n neurex | grep backend'

Scenario: Memory pressure
  1. Check: kubectl top pods -n neurex --sort-by=memory
  2. Scale: ./scaling-guide.sh scale backend 4
  3. Or increase limits: kubectl set resources deployment/neurex-backend \
     --limits=memory=2Gi -n neurex

Scenario: Disk space full
  1. Check: kubectl get pvc -n neurex
  2. Expand: kubectl patch pvc <pvc-name> -n neurex \
     -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'

PROMETHEUS QUERIES:

CPU Utilization:
  avg(rate(container_cpu_usage_seconds_total{pod=~"neurex-.*"}[5m]))

Memory Usage:
  sum(container_memory_usage_bytes{pod=~"neurex-.*"}) / 1024 / 1024

Error Rate:
  rate(http_requests_total{status=~"5.."}[5m])

API Latency (P95):
  histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

For more details, see: docs/PRODUCTION_INFRASTRUCTURE_SETUP.md
EOF
}

# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────

main() {
    case "$COMMAND" in
        monitor)
            monitor_resources
            ;;
        scale)
            if [ $# -lt 2 ]; then
                echo "Usage: ./scaling-guide.sh scale <component> [replicas]"
                exit 1
            fi
            scale_component "$2" "${3:-3}"
            ;;
        hpa-status|hpa)
            hpa_status
            ;;
        optimize)
            optimization_recommendations
            ;;
        bottleneck|bottlenecks)
            find_bottlenecks
            ;;
        decisions)
            scaling_decisions
            ;;
        help|--help|-h|"")
            print_help
            ;;
        *)
            log_warning "Unknown command: $COMMAND"
            print_help
            exit 1
            ;;
    esac
}

main "$@"

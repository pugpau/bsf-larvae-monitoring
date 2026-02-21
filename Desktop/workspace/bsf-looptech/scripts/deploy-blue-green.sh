#!/bin/bash
# BSF-LoopTech Blue-Green Zero-Downtime Deployment
# Usage: ./scripts/deploy-blue-green.sh [init|deploy|rollback|status]

set -euo pipefail

# ── Paths ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
ACTIVE_SLOT_FILE="${PROJECT_DIR}/config/active-slot"
GEN_NGINX="${SCRIPT_DIR}/gen-nginx-conf.sh"

# ── Colour helpers ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()   { echo -e "${GREEN}[INFO]${NC}  $(date '+%H:%M:%S') $1"; }
log_warn()   { echo -e "${YELLOW}[WARN]${NC}  $(date '+%H:%M:%S') $1"; }
log_error()  { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1"; }
log_header() { echo -e "\n${BLUE}══ $1 ══${NC}\n"; }

dc() { docker compose -f "$COMPOSE_FILE" "$@"; }

# ── Slot helpers ──

get_active_slot() {
    if [[ -f "$ACTIVE_SLOT_FILE" ]]; then
        cat "$ACTIVE_SLOT_FILE"
    else
        echo ""
    fi
}

set_active_slot() {
    echo "$1" > "$ACTIVE_SLOT_FILE"
}

opposite_slot() {
    if [[ "$1" == "blue" ]]; then echo "green"; else echo "blue"; fi
}

# ── Ready check ──

wait_for_ready() {
    local host="$1"
    local max_wait=60
    local interval=2
    local elapsed=0

    log_info "Waiting for backend-${host} /ready (max ${max_wait}s)..."

    while (( elapsed < max_wait )); do
        if docker exec "bsf-backend-${host}" curl -sf http://localhost:8000/ready > /dev/null 2>&1; then
            log_info "backend-${host} is ready (${elapsed}s)"
            return 0
        fi
        sleep "$interval"
        elapsed=$(( elapsed + interval ))
    done

    log_error "backend-${host} did not become ready within ${max_wait}s"
    return 1
}

# ══════════════════════════════════════════
# Commands
# ══════════════════════════════════════════

cmd_init() {
    log_header "INIT — First-time setup"

    # 1. Prerequisites
    if ! command -v docker &> /dev/null; then
        log_error "docker not found"; exit 1
    fi

    # 2. Start PostgreSQL
    log_info "Starting PostgreSQL..."
    dc up -d postgres
    log_info "Waiting for PostgreSQL to be healthy..."
    local attempts=0
    while (( attempts < 30 )); do
        if dc exec -T postgres pg_isready -U bsf_user -d bsf_system > /dev/null 2>&1; then
            break
        fi
        sleep 2
        attempts=$(( attempts + 1 ))
    done
    if (( attempts >= 30 )); then
        log_error "PostgreSQL did not become healthy"; exit 1
    fi
    log_info "PostgreSQL is healthy"

    # 3. Build backend
    log_info "Building backend image..."
    dc build backend-blue

    # 4. Run migrations
    log_info "Running Alembic migrations..."
    dc run --rm backend-blue alembic upgrade head

    # 5. Build frontend
    log_info "Building frontend..."
    dc --profile build build frontend-builder
    dc --profile build run --rm frontend-builder echo "Frontend build complete"

    # 6. Generate nginx config → blue
    log_info "Generating nginx config (upstream=backend-blue)..."
    "$GEN_NGINX" backend-blue

    # 7. Start blue backend
    log_info "Starting backend-blue..."
    dc up -d backend-blue

    if ! wait_for_ready "blue"; then
        log_error "backend-blue not ready — stopping"
        dc stop backend-blue
        exit 1
    fi

    # 8. Start router
    log_info "Starting router (nginx)..."
    dc up -d router

    # 9. Persist active slot
    set_active_slot "blue"

    log_header "INIT COMPLETE"
    log_info "Active slot: blue"
    log_info "Frontend:    http://localhost:3000"
    log_info "Health:      http://localhost:3000/health"
}

cmd_deploy() {
    log_header "DEPLOY — Zero-downtime switch"

    local active
    active="$(get_active_slot)"
    if [[ -z "$active" ]]; then
        log_error "No active slot found. Run 'init' first."
        exit 1
    fi

    local target
    target="$(opposite_slot "$active")"
    log_info "Active: ${active} → Target: ${target}"

    # 1. Build target image
    log_info "Building backend-${target}..."
    dc build "backend-${target}"

    # 2. Run migrations (additive — safe for both versions)
    log_info "Running Alembic migrations..."
    dc run --rm "backend-${target}" alembic upgrade head

    # 3. Build frontend
    log_info "Building frontend..."
    dc --profile build build frontend-builder
    dc --profile build run --rm frontend-builder echo "Frontend build complete"

    # 4. Start target backend
    log_info "Starting backend-${target}..."
    dc up -d "backend-${target}"

    # 5. Ready check
    if ! wait_for_ready "$target"; then
        log_error "backend-${target} not ready — aborting deploy"
        dc stop "backend-${target}"
        log_info "Active backend-${active} is unaffected"
        exit 1
    fi

    # 6. Switch nginx upstream
    log_info "Switching nginx upstream → backend-${target}..."
    "$GEN_NGINX" "backend-${target}"
    docker exec bsf-router nginx -s reload

    # 7. Stop old backend
    log_info "Stopping backend-${active}..."
    dc stop "backend-${active}"

    # 8. Persist
    set_active_slot "$target"

    log_header "DEPLOY COMPLETE"
    log_info "Active slot: ${target}"
}

cmd_rollback() {
    log_header "ROLLBACK — Switch to previous slot"

    local active
    active="$(get_active_slot)"
    if [[ -z "$active" ]]; then
        log_error "No active slot found. Run 'init' first."
        exit 1
    fi

    local previous
    previous="$(opposite_slot "$active")"

    # Start previous backend (image already exists)
    log_info "Starting backend-${previous}..."
    dc up -d "backend-${previous}"

    if ! wait_for_ready "$previous"; then
        log_error "backend-${previous} not ready — rollback failed"
        dc stop "backend-${previous}"
        exit 1
    fi

    # Switch nginx
    log_info "Switching nginx upstream → backend-${previous}..."
    "$GEN_NGINX" "backend-${previous}"
    docker exec bsf-router nginx -s reload

    # Stop current
    log_info "Stopping backend-${active}..."
    dc stop "backend-${active}"

    set_active_slot "$previous"

    log_header "ROLLBACK COMPLETE"
    log_info "Active slot: ${previous}"
}

cmd_status() {
    log_header "STATUS"

    local active
    active="$(get_active_slot)"
    if [[ -z "$active" ]]; then
        log_warn "No active slot — system not initialised"
    else
        log_info "Active slot: ${active}"
    fi

    echo ""
    dc ps
}

# ══════════════════════════════════════════
# Entrypoint
# ══════════════════════════════════════════

case "${1:-help}" in
    init)     cmd_init     ;;
    deploy)   cmd_deploy   ;;
    rollback) cmd_rollback ;;
    status)   cmd_status   ;;
    *)
        echo "Usage: $0 {init|deploy|rollback|status}"
        echo ""
        echo "  init      First-time setup (PostgreSQL + migrate + blue backend + router)"
        echo "  deploy    Zero-downtime deploy to the inactive slot"
        echo "  rollback  Instant switch back to previous slot"
        echo "  status    Show active slot and container status"
        exit 1
        ;;
esac

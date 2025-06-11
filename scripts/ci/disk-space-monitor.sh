#!/usr/bin/env bash
set -euo pipefail

# Disk space monitoring utility for CI/CD builds
# Usage: ./disk-space-monitor.sh [check|cleanup|monitor] [description]

ACTION="${1:-check}"
DESCRIPTION="${2:-}"
THRESHOLD_GB="${DISK_SPACE_THRESHOLD_GB:-2}"
CRITICAL_THRESHOLD_GB="${DISK_SPACE_CRITICAL_THRESHOLD_GB:-1}"

function log_info() {
    echo "ℹ️ [$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

function log_warning() {
    echo "⚠️ [$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

function log_error() {
    echo "❌ [$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

function get_disk_usage() {
    df -BG / | awk 'NR==2 {print $4}' | sed 's/G//'
}

function check_disk_space() {
    local available_gb
    available_gb=$(get_disk_usage)
    
    log_info "Available disk space: ${available_gb}GB ${DESCRIPTION:+(${DESCRIPTION})}"
    
    if [[ $available_gb -le $CRITICAL_THRESHOLD_GB ]]; then
        log_error "CRITICAL: Only ${available_gb}GB available (threshold: ${CRITICAL_THRESHOLD_GB}GB)"
        return 2
    elif [[ $available_gb -le $THRESHOLD_GB ]]; then
        log_warning "LOW: Only ${available_gb}GB available (threshold: ${THRESHOLD_GB}GB)"
        return 1
    fi
    
    return 0
}

function cleanup_build_artifacts() {
    log_info "Cleaning up build artifacts to free disk space..."
    
    # Clean up Rust build artifacts
    if [[ -d "target" ]]; then
        log_info "Cleaning Rust target directory..."
        rm -rf target/*/build target/*/deps
        find target -name "*.rlib" -delete || true
        find target -name "*.rmeta" -delete || true
    fi
    
    # Clean up Python build artifacts
    if [[ -d "build" ]]; then
        log_info "Cleaning Python build directory..."
        rm -rf build/
    fi
    
    # Clean up temporary files
    find . -type d -name "__pycache__" -not -path "./.venv*" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -not -path "./.venv*" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -not -path "./.venv*" -delete 2>/dev/null || true
    
    # Clean up test artifacts
    rm -rf .pytest_cache/ .coverage .mypy_cache/ .ruff_cache/ || true
    
    log_info "Build artifact cleanup completed"
}

function cleanup_caches() {
    log_info "Cleaning up caches to free disk space..."
    
    # Clean up sccache if it exists
    if command -v sccache >/dev/null 2>&1; then
        log_info "Cleaning sccache..."
        sccache --stop-server || true
        sccache --start-server || true
    fi
    
    # Clean up uv cache with size limit
    if command -v uv >/dev/null 2>&1; then
        log_info "Pruning uv cache..."
        uv cache prune --keep-versions 2 2>/dev/null || true
    fi
    
    # Clean up cargo cache
    if command -v cargo >/dev/null 2>&1; then
        log_info "Cleaning cargo cache..."
        cargo clean 2>/dev/null || true
    fi
    
    log_info "Cache cleanup completed"
}

function monitor_disk_space() {
    local step="$1"
    log_info "=== Disk Space Monitor: $step ==="
    
    check_disk_space
    local exit_code=$?
    
    if [[ $exit_code -eq 2 ]]; then
        log_error "Critical disk space! Attempting emergency cleanup..."
        cleanup_build_artifacts
        cleanup_caches
        
        # Check again after cleanup
        check_disk_space
        local new_exit_code=$?
        if [[ $new_exit_code -eq 2 ]]; then
            log_error "Emergency cleanup failed to free enough space"
            exit 1
        fi
    elif [[ $exit_code -eq 1 ]]; then
        log_warning "Low disk space detected, running preventive cleanup..."
        cleanup_build_artifacts
    fi
    
    log_info "=== End Disk Space Monitor ==="
}

case "$ACTION" in
    "check")
        check_disk_space
        ;;
    "cleanup")
        cleanup_build_artifacts
        cleanup_caches
        ;;
    "monitor")
        monitor_disk_space "$DESCRIPTION"
        ;;
    *)
        echo "Usage: $0 [check|cleanup|monitor] [description]"
        echo "Environment variables:"
        echo "  DISK_SPACE_THRESHOLD_GB=${THRESHOLD_GB} (warning threshold)"
        echo "  DISK_SPACE_CRITICAL_THRESHOLD_GB=${CRITICAL_THRESHOLD_GB} (critical threshold)"
        exit 1
        ;;
esac
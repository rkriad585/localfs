#!/usr/bin/env bash
set -euo pipefail

PROJECT="localfs"
PYTHON="${PYTHON:-python3}"
PIP="${PIP:-pip3}"

info()  { printf "\033[1;34m[INFO]\033[0m  %s\n" "$*"; }
ok()    { printf "\033[1;32m[OK]\033[0m    %s\n" "$*"; }
err()   { printf "\033[1;31m[ERR]\033[0m   %s\n" "$*"; exit 1; }

cmd() {
    info "$*"
    "$@"
}

build() {
    cmd "$PYTHON" -m build --wheel --sdist .
    ok "Build complete — see dist/"
}

install() {
    cmd "$PIP" install --user -e .
    ok "Installed in editable mode"
}

test_all() {
    cmd "$PYTHON" -m pytest tests/ -v --tb=short
}

lint() {
    cmd "$PYTHON" -m ruff check .
}

format() {
    cmd "$PYTHON" -m ruff format .
}

clean() {
    rm -rf build/ dist/ *.egg-info __pycache__ .pytest_cache .ruff_cache
    find . \( -name __pycache__ -o -name '*.pyc' \) -exec rm -rf {} + 2>/dev/null || true
    ok "Cleaned build artifacts"
}

run() {
    cmd "$PYTHON" -m localfs "$@"
}

docker_build() {
    cmd docker build -t "$PROJECT" .
}

docker_run() {
    docker_run_cmd="${2:-run}"
    cmd docker compose "$docker_run_cmd"
}

case "${1:-help}" in
    build)       build ;;
    install)     install ;;
    test)        test_all ;;
    lint)        lint ;;
    format)      format ;;
    clean)       clean ;;
    run)         shift; run "$@" ;;
    docker)      shift; docker_build "$@" ;;
    help|*)
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  build       Build wheel and sdist"
        echo "  install     Install package in editable mode"
        echo "  test        Run test suite"
        echo "  lint        Run ruff linter"
        echo "  format      Run ruff formatter"
        echo "  clean       Remove build artifacts"
        echo "  run         Start localfs server"
        echo "  docker      Build Docker image"
        echo "  help        Show this help"
        ;;
esac

#!/usr/bin/env bash
set -euo pipefail

# ─── Config ────────────────────────────────────────────────────────────────
PROJECT_NAME="localfs"
GITHUB_USER="rkriad585"
INSTALL_DIR="${HOME}/.${PROJECT_NAME}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/${PROJECT_NAME}"
BIN_DIR="${HOME}/.local/bin"
REPO_URL="https://github.com/${GITHUB_USER}/${PROJECT_NAME}.git"
VERSION_URL="https://raw.githubusercontent.com/${GITHUB_USER}/${PROJECT_NAME}/main/.version"

# ─── Colors ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()   { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_err()  { echo -e "${RED}[ERR]${NC}   $1"; }

# ─── Helpers ───────────────────────────────────────────────────────────────
has_cmd() { command -v "$1" &>/dev/null; }

detect_shell_profile() {
    case "${SHELL:-}" in
        *zsh)  echo "${ZDOTDIR:-$HOME}/.zshrc" ;;
        *bash) [ -n "${BASH_VERSION:-}" ] && echo "${HOME}/.bashrc" || echo "${HOME}/.bash_profile" ;;
        *fish) echo "${HOME}/.config/fish/config.fish" ;;
        *)     echo "${HOME}/.profile" ;;
    esac
}

path_contains() {
    case ":${PATH}:" in
        *":${1}:"*) return 0 ;;
        *) return 1 ;;
    esac
}

ensure_bin_dir() {
    mkdir -p "${BIN_DIR}"
}

add_path_to_profile() {
    local profile="$1"
    local line="export PATH=\"\${PATH}:${BIN_DIR}\""

    if [ ! -f "$profile" ]; then
        touch "$profile"
    fi

    if grep -qsF "export PATH.*${BIN_DIR}" "$profile"; then
        return 0
    fi

    echo "" >> "$profile"
    echo "# Added by ${PROJECT_NAME} installer" >> "$profile"
    echo "${line}" >> "$profile"
    log_ok "Added ${BIN_DIR} to PATH in ${profile}"
}

remove_path_from_profile() {
    local profile="$1"
    if [ ! -f "$profile" ]; then
        return 0
    fi

    local tmp
    tmp=$(mktemp)
    awk -v bin="${BIN_DIR}" '
        /# Added by localfs installer/ { skip=1; next }
        skip && /export PATH/ { skip=0; next }
        { print }
    ' "$profile" > "$tmp" && mv "$tmp" "$profile"

    log_ok "Removed PATH modification from ${profile}"
}

detect_pip() {
    if has_cmd pip3; then echo "pip3"
    elif has_cmd pip; then echo "pip"
    else
        log_err "pip not found. Install Python 3 (pip) and try again."
        exit 1
    fi
}

# ─── Install ───────────────────────────────────────────────────────────────
install_project() {
    echo ""
    echo -e "${BOLD}==> Installing ${PROJECT_NAME}...${NC}"
    echo ""

    # 1. Check prerequisites
    if ! has_cmd git && ! has_cmd curl && ! has_cmd wget; then
        log_err "Need git, curl, or wget to download ${PROJECT_NAME}."
        exit 1
    fi

    # 2. Download / clone
    if [ -d "${INSTALL_DIR}" ]; then
        log_info "${INSTALL_DIR} already exists — updating..."
        if has_cmd git && [ -d "${INSTALL_DIR}/.git" ]; then
            (cd "${INSTALL_DIR}" && git pull --ff-only)
        else
            log_warn "Not a git repo; re-cloning..."
            rm -rf "${INSTALL_DIR}"
            git clone "${REPO_URL}" "${INSTALL_DIR}"
        fi
    else
        log_info "Cloning ${REPO_URL} → ${INSTALL_DIR}"
        if has_cmd git; then
            git clone --depth 1 "${REPO_URL}" "${INSTALL_DIR}"
        else
            local tarball="${REPO_URL}/archive/refs/heads/main.tar.gz"
            mkdir -p "${INSTALL_DIR}"
            if has_cmd curl; then
                curl -fsSL "${tarball}" | tar -xz --strip=1 -C "${INSTALL_DIR}"
            else
                wget -qO- "${tarball}" | tar -xz --strip=1 -C "${INSTALL_DIR}"
            fi
        fi
    fi

    # 3. Install Python package
    local pip
    pip=$(detect_pip)
    log_info "Installing via ${pip} install -e ."
    "${pip}" install --user -e "${INSTALL_DIR}"
    log_ok "${PROJECT_NAME} installed successfully"

    # 4. Ensure bin dir is on PATH
    ensure_bin_dir
    if ! path_contains "${BIN_DIR}"; then
        local profile
        profile=$(detect_shell_profile)
        add_path_to_profile "${profile}"
        log_warn "Restart your shell or run: export PATH=\"\${PATH}:${BIN_DIR}\""
    fi

    # 5. Success banner
    echo ""
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  ${PROJECT_NAME} installed successfully!${NC}"
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  Config directory: ${CONFIG_DIR}"
    echo -e "  Install location: ${INSTALL_DIR}"
    echo ""
    echo -e "  ${YELLOW}Run the command:${NC}"
    echo -e "    ${BOLD}${PROJECT_NAME}${NC}"
    echo ""
}

# ─── Uninstall ─────────────────────────────────────────────────────────────
uninstall_project() {
    echo ""
    echo -e "${BOLD}==> Uninstalling ${PROJECT_NAME}...${NC}"
    echo ""

    # 1. pip uninstall
    local pip
    pip=$(detect_pip)
    if "${pip}" list --format=columns 2>/dev/null | grep -qi "^${PROJECT_NAME}\b"; then
        log_info "Removing Python package..."
        "${pip}" uninstall -y "${PROJECT_NAME}"
        log_ok "Python package removed"
    else
        log_info "${PROJECT_NAME} Python package not found — skipping"
    fi

    # 2. Remove install directory
    if [ -d "${INSTALL_DIR}" ]; then
        rm -rf "${INSTALL_DIR}"
        log_ok "Removed ${INSTALL_DIR}"
    else
        log_info "Install directory not found — skipping"
    fi

    # 3. Remove config directory
    if [ -d "${CONFIG_DIR}" ]; then
        rm -rf "${CONFIG_DIR}"
        log_ok "Removed config directory ${CONFIG_DIR}"
    else
        log_info "Config directory not found — skipping"
    fi

    # 4. Remove PATH entries from shell profiles
    for profile in "${HOME}/.zshrc" "${HOME}/.bashrc" "${HOME}/.bash_profile" "${HOME}/.profile" "${HOME}/.config/fish/config.fish"; do
        if [ -f "$profile" ]; then
            remove_path_from_profile "$profile"
        fi
    done

    echo ""
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  ${PROJECT_NAME} uninstalled.${NC}"
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${YELLOW}Tip:${NC} Restart your shell or reload your profile"
    echo -e "       to remove ${BIN_DIR} from PATH."
    echo ""
}

# ─── Main ──────────────────────────────────────────────────────────────────
main() {
    if [ "${1:-}" = "--selfuninstall" ]; then
        uninstall_project
    else
        install_project
    fi
}

main "$@"

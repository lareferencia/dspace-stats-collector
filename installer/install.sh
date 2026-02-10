#!/usr/bin/env bash
set -euo pipefail

INSTALLER_VERSION="1.0.0"
DEFAULT_REPO_URL="https://github.com/lareferencia/dspace-stats-collector.git"
DEFAULT_INSTALL_PATH="${HOME}/dspace-stats-collector"
DEFAULT_DEV_BRANCH="develop"
MINICONDA_URL_PREFIX="https://repo.anaconda.com/miniconda/"

NON_INTERACTIVE=0
AUTO_YES=0
DEVELOPMENT_MODE=""
SELECTED_RELEASE_REF=""
SELECTED_BRANCH=""
INSTALL_PATH="${DEFAULT_INSTALL_PATH}"
REPO_URL="${DEFAULT_REPO_URL}"
SKIP_CONFIGURE=0

SOURCE_TYPE=""
SOURCE_REF=""
PROFILE_NAME=""
MIN_PYTHON=""
RUNTIME_KIND=""
RUNTIME_PYTHON=""
SRC_PATH=""
ENV_BIN=""
LOG_FILE=""
PREVIOUS_DATA_BACKUP=""
RESTORED_CONFIG=0
RESTORED_STATE=0

info() {
  echo "[INFO] $*"
}

warn() {
  echo "[WARN] $*" >&2
}

error() {
  echo "[ERROR] $*" >&2
}

die() {
  error "$*"
  exit 1
}

cleanup_previous_backup() {
  if [[ -n "${PREVIOUS_DATA_BACKUP}" && -d "${PREVIOUS_DATA_BACKUP}" ]]; then
    rm -rf "${PREVIOUS_DATA_BACKUP}"
  fi
}

trap cleanup_previous_backup EXIT

usage() {
  cat <<'EOF'
DSpace Stats Collector installer

Usage:
  bash installer/install.sh [options]

Options:
  --install-path PATH     Deprecated. Kept for compatibility (path is forced to ~/dspace-stats-collector)
  --repo-url URL          Git repository URL
  --ref REF               Release ref in stable mode (vX.Y, tag:vX.Y, branch:vX.Y)
  --tag TAG               Alias for --ref tag:TAG
  --dev                   Development mode (branch install, editable)
  --no-dev                Force stable mode
  --branch BRANCH         Branch for development mode (default: develop)
  --non-interactive       Do not prompt for input
  --yes                   Assume yes for destructive confirmations
  --skip-configure        Skip dspace-stats-configure step
  -h, --help              Show this help

Examples:
  bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh)
  bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh) -- --non-interactive --yes --ref branch:v1.0
  bash installer/install.sh --dev --branch develop
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --install-path)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --install-path"
        INSTALL_PATH="$1"
        ;;
      --repo-url)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --repo-url"
        REPO_URL="$1"
        ;;
      --ref)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --ref"
        SELECTED_RELEASE_REF="$1"
        ;;
      --tag)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --tag"
        SELECTED_RELEASE_REF="tag:$1"
        ;;
      --branch)
        shift
        [[ $# -gt 0 ]] || die "Missing value for --branch"
        SELECTED_BRANCH="$1"
        ;;
      --dev)
        DEVELOPMENT_MODE="yes"
        ;;
      --no-dev)
        DEVELOPMENT_MODE="no"
        ;;
      --non-interactive)
        NON_INTERACTIVE=1
        ;;
      --yes)
        AUTO_YES=1
        ;;
      --skip-configure)
        SKIP_CONFIGURE=1
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
    shift
  done
}

require_commands() {
  local required=(
    curl
    git
    tar
    gzip
    grep
    sed
    awk
    sort
    tail
    mktemp
    uname
  )
  local missing=()
  local cmd=""

  for cmd in "${required[@]}"; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
      missing+=("${cmd}")
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    die "Missing required system commands: ${missing[*]}. Please install them and rerun."
  fi

  if [[ "$(uname -s)" != "Linux" ]]; then
    die "This installer currently supports Linux only."
  fi
}

prompt_with_default() {
  local prompt="$1"
  local default_value="$2"
  local response=""

  if [[ "${NON_INTERACTIVE}" -eq 1 ]]; then
    echo "${default_value}"
    return
  fi

  read -r -p "${prompt} [${default_value}]: " response
  if [[ -z "${response}" ]]; then
    echo "${default_value}"
  else
    echo "${response}"
  fi
}

prompt_yes_no() {
  local prompt="$1"
  local default_choice="$2"
  local response=""
  local normalized_default="n"

  if [[ "${default_choice}" == "Y" || "${default_choice}" == "y" ]]; then
    normalized_default="y"
  fi

  if [[ "${NON_INTERACTIVE}" -eq 1 ]]; then
    if [[ "${AUTO_YES}" -eq 1 ]]; then
      return 0
    fi
    [[ "${normalized_default}" == "y" ]]
    return
  fi

  while true; do
    if [[ "${normalized_default}" == "y" ]]; then
      read -r -p "${prompt} [Y/n]: " response
      response="${response:-Y}"
    else
      read -r -p "${prompt} [y/N]: " response
      response="${response:-N}"
    fi

    case "${response}" in
      y|Y|yes|YES)
        return 0
        ;;
      n|N|no|NO)
        return 1
        ;;
      *)
        echo "Please answer yes or no."
        ;;
    esac
  done
}

is_versioned_name() {
  local name="$1"
  [[ "${name}" =~ ^v[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]
}

fetch_versioned_remote_refs() {
  local raw_refs=""
  local entries=()

  raw_refs="$(git ls-remote --heads --tags --refs "${REPO_URL}" || true)"
  if [[ -z "${raw_refs}" ]]; then
    die "Could not fetch refs from ${REPO_URL}"
  fi

  while IFS= read -r line; do
    local ref=""
    local name=""
    local kind=""
    local rank=""

    ref="$(echo "${line}" | awk '{print $2}')"
    case "${ref}" in
      refs/tags/*)
        name="${ref#refs/tags/}"
        kind="tag"
        rank="1"
        ;;
      refs/heads/*)
        name="${ref#refs/heads/}"
        kind="branch"
        rank="0"
        ;;
      *)
        continue
        ;;
    esac

    if is_versioned_name "${name}"; then
      entries+=("${name}|${rank}|${kind}")
    fi
  done <<< "${raw_refs}"

  if [[ ${#entries[@]} -eq 0 ]]; then
    die "No versioned refs (vMAJOR.MINOR or vMAJOR.MINOR.PATCH) found in tags/branches at ${REPO_URL}"
  fi

  printf "%s\n" "${entries[@]}" | sort -t'|' -k1,1V -k2,2n
}

versioned_ref_exists() {
  local kind="$1"
  local name="$2"

  case "${kind}" in
    tag)
      git ls-remote --tags --refs "${REPO_URL}" "refs/tags/${name}" | grep -q .
      ;;
    branch)
      git ls-remote --heads --refs "${REPO_URL}" "refs/heads/${name}" | grep -q .
      ;;
    *)
      return 1
      ;;
  esac
}

resolve_release_ref() {
  local selected="$1"
  local kind=""
  local name=""

  if [[ "${selected}" =~ ^(tag|branch):(.+)$ ]]; then
    kind="${BASH_REMATCH[1]}"
    name="${BASH_REMATCH[2]}"
  else
    name="${selected}"
    if versioned_ref_exists "tag" "${name}"; then
      kind="tag"
    elif versioned_ref_exists "branch" "${name}"; then
      kind="branch"
    else
      die "Release ref '${name}' not found as tag or branch in ${REPO_URL}"
    fi
  fi

  if ! is_versioned_name "${name}"; then
    die "Invalid release ref '${name}'. Expected vMAJOR.MINOR(.PATCH)"
  fi

  if ! versioned_ref_exists "${kind}" "${name}"; then
    die "Release ref '${kind}:${name}' does not exist in ${REPO_URL}"
  fi

  SOURCE_TYPE="${kind}"
  SOURCE_REF="${name}"
}

select_source_mode() {
  local versioned_refs=""
  local default_line=""
  local default_version=""
  local default_kind=""
  local default_ref=""
  local selected_ref=""

  if [[ -z "${DEVELOPMENT_MODE}" ]]; then
    if [[ "${NON_INTERACTIVE}" -eq 1 ]]; then
      DEVELOPMENT_MODE="no"
    elif prompt_yes_no "Development mode (editable install from branch)?" "N"; then
      DEVELOPMENT_MODE="yes"
    else
      DEVELOPMENT_MODE="no"
    fi
  fi

  if [[ "${DEVELOPMENT_MODE}" == "yes" ]]; then
    SOURCE_TYPE="branch"
    SOURCE_REF="${SELECTED_BRANCH:-${DEFAULT_DEV_BRANCH}}"
    if [[ "${NON_INTERACTIVE}" -eq 0 && -z "${SELECTED_BRANCH}" ]]; then
      SOURCE_REF="$(prompt_with_default "Development branch" "${DEFAULT_DEV_BRANCH}")"
    fi
    PROFILE_NAME="stable-py310"
    MIN_PYTHON="3.10"
    return
  fi

  versioned_refs="$(fetch_versioned_remote_refs)"
  default_line="$(echo "${versioned_refs}" | tail -n 1)"
  default_version="$(echo "${default_line}" | cut -d'|' -f1)"
  default_kind="$(echo "${default_line}" | cut -d'|' -f3)"
  default_ref="${default_kind}:${default_version}"

  if [[ -n "${SELECTED_RELEASE_REF}" ]]; then
    selected_ref="${SELECTED_RELEASE_REF}"
  else
    selected_ref="$(prompt_with_default "Release ref to install (tag:vX.Y / branch:vX.Y / vX.Y)" "${default_ref}")"
  fi

  resolve_release_ref "${selected_ref}"

  if [[ "${SOURCE_REF}" =~ ^v([0-9]+)\. ]]; then
    local major="${BASH_REMATCH[1]}"
    if (( major >= 1 )); then
      PROFILE_NAME="stable-py310"
      MIN_PYTHON="3.10"
    else
      PROFILE_NAME="legacy-py38"
      MIN_PYTHON="3.8"
    fi
  else
    die "Invalid release ref format '${SOURCE_REF}'. Expected vMAJOR.MINOR(.PATCH)"
  fi
}

python_meets_minimum() {
  local python_cmd="$1"
  local minimum="$2"
  local current=""
  local min_major=""
  local min_minor=""

  current="$("${python_cmd}" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || true)"
  if [[ -z "${current}" ]]; then
    return 1
  fi

  min_major="$(echo "${minimum}" | cut -d. -f1)"
  min_minor="$(echo "${minimum}" | cut -d. -f2)"

  "${python_cmd}" - <<PY
import sys
major, minor = sys.version_info[:2]
min_major = int("${min_major}")
min_minor = int("${min_minor}")
sys.exit(0 if (major, minor) >= (min_major, min_minor) else 1)
PY
}

find_compatible_python() {
  local minimum="$1"
  local candidate=""

  for candidate in python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      if python_meets_minimum "${candidate}" "${minimum}"; then
        echo "${candidate}"
        return 0
      fi
    fi
  done
  return 1
}

backup_existing_runtime_data() {
  local backup_root=""
  local has_backup=0

  backup_root="$(mktemp -d "${TMPDIR:-/tmp}/dspace-installer-backup.XXXXXX")"

  if [[ -d "${INSTALL_PATH}/config" ]]; then
    mkdir -p "${backup_root}/config"
    cp -a "${INSTALL_PATH}/config/." "${backup_root}/config/"
    has_backup=1
  fi

  if [[ -d "${INSTALL_PATH}/var/state" ]]; then
    mkdir -p "${backup_root}/var/state"
    cp -a "${INSTALL_PATH}/var/state/." "${backup_root}/var/state/"
    has_backup=1
  fi

  if [[ "${has_backup}" -eq 1 ]]; then
    PREVIOUS_DATA_BACKUP="${backup_root}"
    info "Backed up existing config/state from previous installation."
  else
    rm -rf "${backup_root}"
  fi
}

restore_previous_runtime_data() {
  if [[ -z "${PREVIOUS_DATA_BACKUP}" || ! -d "${PREVIOUS_DATA_BACKUP}" ]]; then
    return
  fi

  if [[ -d "${PREVIOUS_DATA_BACKUP}/config" ]]; then
    mkdir -p "${INSTALL_PATH}/config"
    cp -a "${PREVIOUS_DATA_BACKUP}/config/." "${INSTALL_PATH}/config/"
    RESTORED_CONFIG=1
  fi

  if [[ -d "${PREVIOUS_DATA_BACKUP}/var/state" ]]; then
    mkdir -p "${INSTALL_PATH}/var/state"
    cp -a "${PREVIOUS_DATA_BACKUP}/var/state/." "${INSTALL_PATH}/var/state/"
    RESTORED_STATE=1
  fi

  cleanup_previous_backup
  PREVIOUS_DATA_BACKUP=""
}

ensure_install_path() {
  if [[ "${INSTALL_PATH}" != "${DEFAULT_INSTALL_PATH}" ]]; then
    warn "Custom install paths are disabled for compatibility. Using ${DEFAULT_INSTALL_PATH}."
    INSTALL_PATH="${DEFAULT_INSTALL_PATH}"
  fi

  if [[ -z "${INSTALL_PATH}" || "${INSTALL_PATH}" == "/" ]]; then
    die "Invalid install path '${INSTALL_PATH}'"
  fi

  if [[ -e "${INSTALL_PATH}" ]]; then
    if prompt_yes_no "Directory '${INSTALL_PATH}' exists and will be removed. Continue?" "N"; then
      backup_existing_runtime_data
      rm -rf "${INSTALL_PATH}"
    else
      die "Installation aborted by user."
    fi
  fi

  mkdir -p "${INSTALL_PATH}/src" "${INSTALL_PATH}/var/logs"

  LOG_FILE="${INSTALL_PATH}/var/logs/installer-$(date -u +%Y%m%dT%H%M%SZ).log"
  exec > >(tee -a "${LOG_FILE}") 2>&1
}

clone_source() {
  SRC_PATH="${INSTALL_PATH}/src/dspace-stats-collector"
  info "Cloning source code from ${REPO_URL}"

  if [[ "${SOURCE_TYPE}" == "tag" ]]; then
    git clone "${REPO_URL}" "${SRC_PATH}"
    (
      cd "${SRC_PATH}"
      git checkout "refs/tags/${SOURCE_REF}"
    )
  else
    git clone --depth 1 --branch "${SOURCE_REF}" "${REPO_URL}" "${SRC_PATH}"
  fi
}

write_fallback_requirements() {
  local profile="$1"
  local target_file="$2"

  case "${profile}" in
    stable-py310)
      cat > "${target_file}" <<'EOF'
requests>=2.31,<3
pyjavaprops>=1.0.2,<2
SQLAlchemy>=2.0,<3
psycopg2-binary>=2.9,<3
pysolr>=3.9,<4
pandas>=2.1,<3
urllib3>=1.26,<3
pytz>=2023.3
python-crontab>=2.7,<4
anonymizeip
pid
tenacity>=8.2,<10
EOF
      ;;
    legacy-py38)
      cat > "${target_file}" <<'EOF'
requests>=2.25,<2.33
pyjavaprops==1.0.2
SQLAlchemy>=1.4,<2.0
psycopg2-binary>=2.8,<3
pysolr>=3.8,<4
pandas>=1.2,<2.0
urllib3>=1.24,<2.0
pytz>=2018.7,<2025.0
python-crontab>=2.6,<4
anonymizeip
pid
tenacity>=7,<9
EOF
      ;;
    *)
      die "Unknown requirements profile: ${profile}"
      ;;
  esac
}

resolve_requirements_file() {
  local in_repo_file="${SRC_PATH}/installer/requirements/${PROFILE_NAME}.txt"
  local fallback_file="${INSTALL_PATH}/requirements-${PROFILE_NAME}.txt"

  if [[ -f "${in_repo_file}" ]]; then
    echo "${in_repo_file}"
    return
  fi

  warn "Repository ref '${SOURCE_REF}' does not provide installer requirements for ${PROFILE_NAME}. Using fallback profile."
  write_fallback_requirements "${PROFILE_NAME}" "${fallback_file}"
  echo "${fallback_file}"
}

accept_conda_tos() {
  local conda_bin="$1"
  if "${conda_bin}" tos --help >/dev/null 2>&1; then
    "${conda_bin}" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true
    "${conda_bin}" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true
  fi
}

miniconda_installer_for_machine() {
  case "$(uname -m)" in
    x86_64)
      echo "Miniconda3-latest-Linux-x86_64.sh"
      ;;
    aarch64|arm64)
      echo "Miniconda3-latest-Linux-aarch64.sh"
      ;;
    *)
      die "Unsupported CPU architecture for Miniconda: $(uname -m)"
      ;;
  esac
}

setup_runtime() {
  local requirements_file="$1"
  local venv_bin=""

  if RUNTIME_PYTHON="$(find_compatible_python "${MIN_PYTHON}")"; then
    info "Using system Python '${RUNTIME_PYTHON}' (minimum required: ${MIN_PYTHON})"

    if "${RUNTIME_PYTHON}" -m venv --help >/dev/null 2>&1; then
      local venv_path="${INSTALL_PATH}/venv"
      "${RUNTIME_PYTHON}" -m venv "${venv_path}"
      venv_bin="${venv_path}/bin"
      ENV_BIN="${venv_bin}"
      RUNTIME_KIND="venv"
    else
      warn "System Python found but venv module is unavailable. Falling back to Miniconda."
      RUNTIME_KIND="miniconda"
    fi
  else
    warn "No compatible system Python found (minimum required: ${MIN_PYTHON}). Falling back to Miniconda."
    RUNTIME_KIND="miniconda"
  fi

  if [[ "${RUNTIME_KIND}" == "miniconda" ]]; then
    local miniconda_file=""
    local miniconda_url=""
    local miniconda_installer=""
    local conda_root="${INSTALL_PATH}/miniconda"
    local conda_env="${conda_root}/envs/collector"

    miniconda_file="$(miniconda_installer_for_machine)"
    miniconda_url="${MINICONDA_URL_PREFIX}${miniconda_file}"
    miniconda_installer="${INSTALL_PATH}/miniconda-installer.sh"

    info "Downloading Miniconda from ${miniconda_url}"
    curl -fsSL "${miniconda_url}" -o "${miniconda_installer}"

    info "Installing Miniconda in ${conda_root}"
    bash "${miniconda_installer}" -b -f -p "${conda_root}"
    rm -f "${miniconda_installer}"

    accept_conda_tos "${conda_root}/bin/conda"

    info "Creating conda environment with Python ${MIN_PYTHON}"
    "${conda_root}/bin/conda" create -y -p "${conda_env}" "python=${MIN_PYTHON}" pip
    ENV_BIN="${conda_env}/bin"
  fi

  info "Installing runtime dependencies (${PROFILE_NAME})"
  "${ENV_BIN}/pip" install --upgrade pip "setuptools<81" wheel
  "${ENV_BIN}/pip" install -r "${requirements_file}"
}

install_collector() {
  info "Installing dspace-stats-collector from source"
  if [[ "${DEVELOPMENT_MODE}" == "yes" ]]; then
    "${ENV_BIN}/pip" install --no-cache-dir -e "${SRC_PATH}"
  else
    "${ENV_BIN}/pip" install --no-cache-dir "${SRC_PATH}"
  fi

  "${ENV_BIN}/pip" check
}

create_bin_symlinks() {
  local target_bin_dir="${INSTALL_PATH}/bin"
  local command_name=""
  local commands=(
    python
    pip
    dspace-stats-collector
    dspace-stats-configure
    dspace-stats-cronify
    dspace-stats-export
  )

  mkdir -p "${target_bin_dir}"

  for command_name in "${commands[@]}"; do
    if [[ -x "${ENV_BIN}/${command_name}" ]]; then
      ln -sfn "${ENV_BIN}/${command_name}" "${target_bin_dir}/${command_name}"
    fi
  done
}

run_post_configure() {
  if [[ "${SKIP_CONFIGURE}" -eq 1 ]]; then
    info "Skipping post-install configuration step by request."
    return
  fi

  info "Creating default configuration files"
  "${INSTALL_PATH}/bin/dspace-stats-configure" -c "${INSTALL_PATH}/config" -r default
}

print_summary() {
  local restored_config="no"
  local restored_state="no"

  if [[ "${RESTORED_CONFIG}" -eq 1 ]]; then
    restored_config="yes"
  fi
  if [[ "${RESTORED_STATE}" -eq 1 ]]; then
    restored_state="yes"
  fi

  cat <<EOF

Installation completed.

Summary:
  Source mode:           ${SOURCE_TYPE}
  Source ref:            ${SOURCE_REF}
  Development mode:      ${DEVELOPMENT_MODE}
  Runtime profile:       ${PROFILE_NAME}
  Runtime type:          ${RUNTIME_KIND}
  Install path:          ${INSTALL_PATH}
  Source path:           ${SRC_PATH}
  Binary path:           ${INSTALL_PATH}/bin
  Config path:           ${INSTALL_PATH}/config
  Previous config kept:  ${restored_config}
  Previous state kept:   ${restored_state}
  Installer log:         ${LOG_FILE}

Next steps:
  1. Replace ${INSTALL_PATH}/config/default.properties with your repository-specific file.
  2. Test run:
       ${INSTALL_PATH}/bin/dspace-stats-collector -f YYYY-MM-DD --verbose -c ${INSTALL_PATH}/config
  3. Optional cron setup:
       ${INSTALL_PATH}/bin/dspace-stats-cronify -c ${INSTALL_PATH}/config

EOF
}

main() {
  parse_args "$@"
  require_commands
  select_source_mode
  ensure_install_path

  info "Starting installer v${INSTALLER_VERSION}"
  info "Repository: ${REPO_URL}"
  info "Install path: ${INSTALL_PATH}"
  info "Selected ref: ${SOURCE_TYPE}:${SOURCE_REF}"

  clone_source
  local requirements_file=""
  requirements_file="$(resolve_requirements_file)"
  setup_runtime "${requirements_file}"
  install_collector
  create_bin_symlinks
  run_post_configure
  restore_previous_runtime_data
  print_summary
}

main "$@"

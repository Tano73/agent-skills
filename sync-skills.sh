#!/usr/bin/env bash
# =============================================================================
# sync-skills.sh
# Purpose : Bidirectional sync between repo skills/ and $HOME/.agents/skills/
# Usage   : ./sync-skills.sh [status|sync] [-h|--help]
# Author  : <author>
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# ANSI color helpers — only emit codes when the terminal supports ≥ 8 colors
# ---------------------------------------------------------------------------
if [ -t 1 ] && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
  C_GREEN="\033[0;32m"
  C_YELLOW="\033[0;33m"
  C_CYAN="\033[0;36m"
  C_MAGENTA="\033[0;35m"
  C_RED="\033[0;31m"
  C_RESET="\033[0m"
else
  C_GREEN="" C_YELLOW="" C_CYAN="" C_MAGENTA="" C_RED="" C_RESET=""
fi

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
  cat <<EOF
Usage: $(basename "$0") [status|sync] [-h|--help]

Commands:
  status  (default) Show sync state of each skill — exits 1 if any differ.
  sync              Interactive bidirectional sync, one skill at a time.

Options:
  -h, --help        Print this help and exit.

Directories:
  Repo skills  : <repo-root>/skills/
  Install dir  : \$HOME/.agents/skills/
EOF
}

# ---------------------------------------------------------------------------
# Detect repo root — abort if not inside a git repository
# ---------------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null \
  || { echo -e "${C_RED}Error: not inside a git repository.${C_RESET}" >&2; exit 2; })"

SKILLS_DIR="${REPO_ROOT}/skills"
INSTALL_DIR="${HOME}/.agents/skills"

# ---------------------------------------------------------------------------
# SHA-256 helper: compute a single fingerprint for an entire directory.
# Hashes all file contents sorted by relative path, then hashes the result.
# ---------------------------------------------------------------------------
dir_sha256() {
  local dir="$1"
  # Auto-detect the available sha tool
  if command -v sha256sum &>/dev/null; then
    local sha_cmd="sha256sum"
  elif command -v shasum &>/dev/null; then
    local sha_cmd="shasum -a 256"
  else
    echo -e "${C_RED}Error: neither sha256sum nor shasum found.${C_RESET}" >&2
    exit 2
  fi

  # Find all regular files, sort by relative path, hash each, then hash the list
  find "$dir" -type f \
    | sed "s|^${dir}/||" \
    | sort \
    | while IFS= read -r rel; do
        $sha_cmd "${dir}/${rel}"
      done \
    | $sha_cmd \
    | awk '{print $1}'
}

# ---------------------------------------------------------------------------
# copy_dir <src> <dst>
# Uses rsync if available, otherwise falls back to rm+cp.
# ---------------------------------------------------------------------------
copy_dir() {
  local src="$1" dst="$2"
  if command -v rsync &>/dev/null; then
    rsync -a --delete "${src}/" "${dst}/"
  else
    rm -rf "$dst"
    cp -r "$src" "$dst"
  fi
}

# ---------------------------------------------------------------------------
# skill_status <skill_name>  →  prints one status line, returns state string
# ---------------------------------------------------------------------------
SEPARATOR="─────────────────────────────────────────────────────"

skill_status_line() {
  local skill="$1"
  local repo_dir="${SKILLS_DIR}/${skill}"
  local inst_dir="${INSTALL_DIR}/${skill}"
  local in_repo=false in_install=false

  [ -d "$repo_dir" ]    && in_repo=true
  [ -d "$inst_dir" ]    && in_install=true

  if $in_repo && $in_install; then
    local repo_hash inst_hash
    repo_hash="$(dir_sha256 "$repo_dir")"
    inst_hash="$(dir_sha256 "$inst_dir")"
    if [ "$repo_hash" = "$inst_hash" ]; then
      printf "  ${C_GREEN}✓ IN SYNC       ${C_RESET} %s\n" "$skill"
      echo "IN_SYNC"
    else
      printf "  ${C_YELLOW}≠ DIFFERS       ${C_RESET} %s\n" "$skill"
      echo "DIFFERS"
    fi
  elif $in_repo && ! $in_install; then
    printf "  ${C_CYAN}→ REPO ONLY     ${C_RESET} %s\n" "$skill"
    echo "REPO_ONLY"
  else
    printf "  ${C_MAGENTA}← INSTALL ONLY  ${C_RESET} %s\n" "$skill"
    echo "INSTALL_ONLY"
  fi
}

# ---------------------------------------------------------------------------
# Collect the full list of skills to inspect:
#   - all subdirs under skills/ (repo-side)
#   - plus any subdir under $INSTALL_DIR whose name matches a skill absent in repo
#     but was previously pushed (install-only detection)
# ---------------------------------------------------------------------------
collect_skills() {
  local skills=()

  # Skills present in the repo
  for d in "${SKILLS_DIR}"/*/; do
    [ -d "$d" ] && skills+=("$(basename "$d")")
  done

  # Skills present only in the install dir (not in repo)
  if [ -d "$INSTALL_DIR" ]; then
    for d in "${INSTALL_DIR}"/*/; do
      [ -d "$d" ] || continue
      local name
      name="$(basename "$d")"
      # Include only if the install-only skill came from *this* repo's skill set.
      # Strategy: check if there is a SKILL.md inside — our convention.
      if [ ! -d "${SKILLS_DIR}/${name}" ] && [ -f "${INSTALL_DIR}/${name}/SKILL.md" ]; then
        skills+=("$name")
      fi
    done
  fi

  # Deduplicate and sort
  printf '%s\n' "${skills[@]}" | sort -u
}

# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------
cmd_status() {
  mkdir -p "$INSTALL_DIR"

  local n_total=0 n_sync=0 n_differs=0 n_repo=0 n_install=0
  local out_differs=() out_repo=() out_install=()

  echo
  echo "  Repo skills  : ${SKILLS_DIR}"
  echo "  Install dir  : ${INSTALL_DIR}"
  echo "  ${SEPARATOR:0:50}"
  echo

  # skill_status_line prints the display line to stdout AND returns the state
  # on the next line. We capture both via a temp approach using a subshell.
  while IFS= read -r skill; do
    n_total=$((n_total + 1))
    # Run in subshell; first line = display, second line = state token
    local combined
    combined="$(skill_status_line "$skill" 2>&1)"
    local display state
    display="$(echo "$combined" | head -n1)"
    state="$(echo "$combined" | tail -n1)"

    echo "$display"

    case "$state" in
      IN_SYNC)      n_sync=$((n_sync + 1)) ;;
      DIFFERS)      n_differs=$((n_differs + 1)); out_differs+=("$skill") ;;
      REPO_ONLY)    n_repo=$((n_repo + 1));    out_repo+=("$skill") ;;
      INSTALL_ONLY) n_install=$((n_install + 1)); out_install+=("$skill") ;;
    esac
  done < <(collect_skills)

  echo
  echo "  ${SEPARATOR:0:50}"
  printf "  %d skills checked · %d in sync · %d differ · %d repo-only · %d install-only\n" \
    "$n_total" "$n_sync" "$n_differs" "$n_repo" "$n_install"
  echo

  # Exit 1 if anything is out of sync
  [ $((n_differs + n_repo + n_install)) -eq 0 ]
}

# ---------------------------------------------------------------------------
# sync command
# ---------------------------------------------------------------------------
cmd_sync() {
  mkdir -p "$INSTALL_DIR"

  local actions_taken=()

  echo
  echo "  Repo skills  : ${SKILLS_DIR}"
  echo "  Install dir  : ${INSTALL_DIR}"
  echo "  ${SEPARATOR:0:50}"
  echo

  while IFS= read -r skill; do
    local repo_dir="${SKILLS_DIR}/${skill}"
    local inst_dir="${INSTALL_DIR}/${skill}"

    # Determine state
    local state
    if [ -d "$repo_dir" ] && [ -d "$inst_dir" ]; then
      local rh ih
      rh="$(dir_sha256 "$repo_dir")"
      ih="$(dir_sha256 "$inst_dir")"
      [ "$rh" = "$ih" ] && state="IN_SYNC" || state="DIFFERS"
    elif [ -d "$repo_dir" ]; then
      state="REPO_ONLY"
    else
      state="INSTALL_ONLY"
    fi

    # Skip skills already in sync
    if [ "$state" = "IN_SYNC" ]; then
      printf "  ${C_GREEN}✓ IN SYNC       ${C_RESET} %s — skipping\n" "$skill"
      continue
    fi

    echo
    printf "  ${C_YELLOW}▶ %s${C_RESET}  [%s]\n" "$skill" "$state"

    # Show a brief diff summary
    if [ "$state" = "DIFFERS" ]; then
      echo "  Changes:"
      diff -rq "$repo_dir" "$inst_dir" 2>/dev/null | sed 's/^/    /' || true
    elif [ "$state" = "REPO_ONLY" ]; then
      echo "  Not present in install dir."
    else
      echo "  Not present in repo."
    fi

    echo
    echo "    [p] push  repo → install"
    echo "    [u] pull  install → repo"
    echo "    [s] skip"

    local choice=""
    while [[ ! "$choice" =~ ^[pPuUsS]$ ]]; do
      read -rp "    Choice [p/u/s]: " choice
    done

    case "${choice,,}" in
      p)
        copy_dir "$repo_dir" "$inst_dir"
        printf "  ${C_GREEN}✓ pushed${C_RESET} %s → install\n" "$skill"
        actions_taken+=("pushed: $skill")
        ;;
      u)
        copy_dir "$inst_dir" "$repo_dir"
        printf "  ${C_GREEN}✓ pulled${C_RESET} %s → repo\n" "$skill"
        actions_taken+=("pulled: $skill")
        ;;
      s)
        printf "  ${C_YELLOW}⊘ skipped${C_RESET} %s\n" "$skill"
        actions_taken+=("skipped: $skill")
        ;;
    esac
  done < <(collect_skills)

  echo
  echo "  ${SEPARATOR:0:50}"
  echo "  Sync complete. Actions taken: ${#actions_taken[@]}"
  for a in "${actions_taken[@]:-}"; do
    [ -n "$a" ] && echo "    • $a"
  done
  echo
}

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
CMD="${1:-status}"

case "$CMD" in
  -h|--help)  usage; exit 0 ;;
  status)     cmd_status ;;
  sync)       cmd_sync ;;
  *)
    echo -e "${C_RED}Unknown command: $CMD${C_RESET}" >&2
    usage >&2
    exit 2
    ;;
esac

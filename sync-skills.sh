#!/usr/bin/env bash
# =============================================================================
# sync-skills.sh
# Purpose : Bidirectional sync between repo skills/ and $HOME/.agents/skills/
#           and between repo instructions/ and $HOME/.agents/instructions/
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
Usage: $(basename "$0") [status|sync] [--all] [-h|--help]

Commands:
  status       (default) Show sync state of each skill and instruction — exits 1 if any differ.
  sync         Interactive bidirectional sync for REPO_ONLY and DIFFERS items.
  sync --all   Also include INSTALL_ONLY items in the sync session.

Options:
  -h, --help        Print this help and exit.

Directories:
  Repo skills        : <repo-root>/skills/
  Install skills     : \$HOME/.agents/skills/
  Repo instructions  : <repo-root>/instructions/
  Install instructions: \$HOME/.agents/instructions/

Default choices during sync:
  REPO_ONLY / DIFFERS  → push  (repo is the source of truth)
  INSTALL_ONLY         → skip
EOF
}

# ---------------------------------------------------------------------------
# Detect repo root — abort if not inside a git repository
# ---------------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null \
  || { echo -e "${C_RED}Error: not inside a git repository.${C_RESET}" >&2; exit 2; })"

SKILLS_DIR="${REPO_ROOT}/skills"
INSTALL_DIR="${HOME}/.agents/skills"
INSTRUCTIONS_DIR="${REPO_ROOT}/instructions"
INSTRUCTIONS_INSTALL_DIR="${HOME}/.agents/instructions"

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

  # Find all regular files, sort by relative path, hash each file's content
  # only (strip the absolute path from sha output so the combined hash is
  # path-independent), then hash the full list.
  find "$dir" -type f \
    | sed "s|^${dir}/||" \
    | sort \
    | while IFS= read -r rel; do
        $sha_cmd "${dir}/${rel}" | awk '{print $1}'
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
# file_sha256 <file>  →  prints the SHA-256 hash of a single file
# ---------------------------------------------------------------------------
file_sha256() {
  local file="$1"
  if command -v sha256sum &>/dev/null; then
    sha256sum "$file" | awk '{print $1}'
  elif command -v shasum &>/dev/null; then
    shasum -a 256 "$file" | awk '{print $1}'
  else
    echo -e "${C_RED}Error: neither sha256sum nor shasum found.${C_RESET}" >&2
    exit 2
  fi
}

# ---------------------------------------------------------------------------
# copy_file <src> <dst>  →  copies a single file, creating parent dirs
# ---------------------------------------------------------------------------
copy_file() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
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
# instruction_status_line <filename>
# Like skill_status_line but works on individual .md files in instructions/
# ---------------------------------------------------------------------------
instruction_status_line() {
  local name="$1"
  local repo_file="${INSTRUCTIONS_DIR}/${name}"
  local inst_file="${INSTRUCTIONS_INSTALL_DIR}/${name}"
  local in_repo=false in_install=false

  [ -f "$repo_file" ]  && in_repo=true
  [ -f "$inst_file" ]  && in_install=true

  if $in_repo && $in_install; then
    local repo_hash inst_hash
    repo_hash="$(file_sha256 "$repo_file")"
    inst_hash="$(file_sha256 "$inst_file")"
    if [ "$repo_hash" = "$inst_hash" ]; then
      printf "  ${C_GREEN}✓ IN SYNC       ${C_RESET} %s\n" "$name"
      echo "IN_SYNC"
    else
      printf "  ${C_YELLOW}≠ DIFFERS       ${C_RESET} %s\n" "$name"
      echo "DIFFERS"
    fi
  elif $in_repo && ! $in_install; then
    printf "  ${C_CYAN}→ REPO ONLY     ${C_RESET} %s\n" "$name"
    echo "REPO_ONLY"
  else
    printf "  ${C_MAGENTA}← INSTALL ONLY  ${C_RESET} %s\n" "$name"
    echo "INSTALL_ONLY"
  fi
}

# ---------------------------------------------------------------------------
# collect_instructions  →  prints sorted list of instruction file names
# ---------------------------------------------------------------------------
collect_instructions() {
  local names=()

  if [ -d "$INSTRUCTIONS_DIR" ]; then
    for f in "${INSTRUCTIONS_DIR}"/*.md; do
      [ -f "$f" ] && names+=("$(basename "$f")")
    done
  fi

  if [ -d "$INSTRUCTIONS_INSTALL_DIR" ]; then
    for f in "${INSTRUCTIONS_INSTALL_DIR}"/*.md; do
      [ -f "$f" ] || continue
      local name
      name="$(basename "$f")"
      if [ ! -f "${INSTRUCTIONS_DIR}/${name}" ]; then
        names+=("$name")
      fi
    done
  fi

  printf '%s\n' "${names[@]}" | sort -u
}

# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------
cmd_status() {
  mkdir -p "$INSTALL_DIR"
  mkdir -p "$INSTRUCTIONS_INSTALL_DIR"

  local n_total=0 n_sync=0 n_differs=0 n_repo=0 n_install=0
  local out_differs=() out_repo=() out_install=()

  echo
  echo "  ── Skills ────────────────────────────────────────"
  echo "  Repo         : ${SKILLS_DIR}"
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

  # --- Instructions section ---
  local ni_total=0 ni_sync=0 ni_differs=0 ni_repo=0 ni_install=0

  echo
  echo "  ── Instructions ──────────────────────────────────"
  echo "  Repo         : ${INSTRUCTIONS_DIR}"
  echo "  Install dir  : ${INSTRUCTIONS_INSTALL_DIR}"
  echo "  ${SEPARATOR:0:50}"
  echo

  while IFS= read -r name; do
    ni_total=$((ni_total + 1))
    local combined
    combined="$(instruction_status_line "$name" 2>&1)"
    local display state
    display="$(echo "$combined" | head -n1)"
    state="$(echo "$combined" | tail -n1)"

    echo "$display"

    case "$state" in
      IN_SYNC)      ni_sync=$((ni_sync + 1)) ;;
      DIFFERS)      ni_differs=$((ni_differs + 1)) ;;
      REPO_ONLY)    ni_repo=$((ni_repo + 1)) ;;
      INSTALL_ONLY) ni_install=$((ni_install + 1)) ;;
    esac
  done < <(collect_instructions)

  echo
  echo "  ${SEPARATOR:0:50}"
  printf "  %d instructions checked · %d in sync · %d differ · %d repo-only · %d install-only\n" \
    "$ni_total" "$ni_sync" "$ni_differs" "$ni_repo" "$ni_install"
  echo

  # Exit 1 if anything is out of sync (skills or instructions)
  [ $((n_differs + n_repo + n_install + ni_differs + ni_repo + ni_install)) -eq 0 ]
}

# ---------------------------------------------------------------------------
# sync command
# $1 : "all" to include INSTALL_ONLY skills, empty otherwise
# ---------------------------------------------------------------------------
cmd_sync() {
  local include_install_only="${1:-}"
  mkdir -p "$INSTALL_DIR"
  mkdir -p "$INSTRUCTIONS_INSTALL_DIR"

  local actions_taken=()

  # Collect all items into arrays BEFORE the interactive loops so that stdin
  # remains connected to the terminal and plain `read -rp` works without tricks.
  local -a all_skills all_instructions
  mapfile -t all_skills       < <(collect_skills)
  mapfile -t all_instructions < <(collect_instructions)

  echo
  echo "  ── Skills ────────────────────────────────────────"
  echo "  Repo         : ${SKILLS_DIR}"
  echo "  Install dir  : ${INSTALL_DIR}"
  echo "  ${SEPARATOR:0:50}"
  echo

  for skill in "${all_skills[@]}"; do
    local repo_dir="${SKILLS_DIR}/${skill}"
    local inst_dir="${INSTALL_DIR}/${skill}"

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

    if [ "$state" = "IN_SYNC" ]; then
      printf "  ${C_GREEN}✓ IN SYNC       ${C_RESET} %s — skipping\n" "$skill"
      continue
    fi
    if [ "$state" = "INSTALL_ONLY" ] && [ -z "$include_install_only" ]; then
      continue
    fi

    echo
    printf "  ${C_YELLOW}▶ %s${C_RESET}  [%s]\n" "$skill" "$state"

    if [ "$state" = "DIFFERS" ]; then
      echo "  Changes:"
      diff -rq "$repo_dir" "$inst_dir" 2>/dev/null | sed 's/^/    /' || true
    elif [ "$state" = "REPO_ONLY" ]; then
      echo "  Not present in install dir."
    else
      echo "  Not present in repo."
    fi

    local default_choice
    case "$state" in
      REPO_ONLY|DIFFERS) default_choice="p" ;;
      INSTALL_ONLY)      default_choice="s" ;;
    esac

    echo
    echo "    [p] push  repo → install"
    echo "    [u] pull  install → repo"
    echo "    [s] skip"

    local choice
    while true; do
      read -rp "    Choice [p/u/s, default=${default_choice}]: " choice
      [[ "$choice" =~ ^[pPuUsS]?$ ]] && break
    done
    [ -z "$choice" ] && choice="$default_choice"

    case "${choice,,}" in
      p)
        copy_dir "$repo_dir" "$inst_dir"
        printf "  ${C_GREEN}✓ pushed${C_RESET} %s → install\n" "$skill"
        actions_taken+=("pushed skill: $skill")
        ;;
      u)
        copy_dir "$inst_dir" "$repo_dir"
        printf "  ${C_GREEN}✓ pulled${C_RESET} %s → repo\n" "$skill"
        actions_taken+=("pulled skill: $skill")
        ;;
      s)
        printf "  ${C_YELLOW}⊘ skipped${C_RESET} %s\n" "$skill"
        actions_taken+=("skipped skill: $skill")
        ;;
    esac
  done

  # --- Instructions ---
  echo
  echo "  ── Instructions ──────────────────────────────────"
  echo "  Repo         : ${INSTRUCTIONS_DIR}"
  echo "  Install dir  : ${INSTRUCTIONS_INSTALL_DIR}"
  echo "  ${SEPARATOR:0:50}"
  echo

  for name in "${all_instructions[@]}"; do
    local repo_file="${INSTRUCTIONS_DIR}/${name}"
    local inst_file="${INSTRUCTIONS_INSTALL_DIR}/${name}"

    local state
    if [ -f "$repo_file" ] && [ -f "$inst_file" ]; then
      local rh ih
      rh="$(file_sha256 "$repo_file")"
      ih="$(file_sha256 "$inst_file")"
      [ "$rh" = "$ih" ] && state="IN_SYNC" || state="DIFFERS"
    elif [ -f "$repo_file" ]; then
      state="REPO_ONLY"
    else
      state="INSTALL_ONLY"
    fi

    if [ "$state" = "IN_SYNC" ]; then
      printf "  ${C_GREEN}✓ IN SYNC       ${C_RESET} %s — skipping\n" "$name"
      continue
    fi
    if [ "$state" = "INSTALL_ONLY" ] && [ -z "$include_install_only" ]; then
      continue
    fi

    echo
    printf "  ${C_YELLOW}▶ %s${C_RESET}  [%s]\n" "$name" "$state"

    if [ "$state" = "DIFFERS" ]; then
      echo "  Changes:"
      diff "$repo_file" "$inst_file" 2>/dev/null | head -20 | sed 's/^/    /' || true
    elif [ "$state" = "REPO_ONLY" ]; then
      echo "  Not present in install dir."
    else
      echo "  Not present in repo."
    fi

    local default_choice
    case "$state" in
      REPO_ONLY|DIFFERS) default_choice="p" ;;
      INSTALL_ONLY)      default_choice="s" ;;
    esac

    echo
    echo "    [p] push  repo → install"
    echo "    [u] pull  install → repo"
    echo "    [s] skip"

    local choice
    while true; do
      read -rp "    Choice [p/u/s, default=${default_choice}]: " choice
      [[ "$choice" =~ ^[pPuUsS]?$ ]] && break
    done
    [ -z "$choice" ] && choice="$default_choice"

    case "${choice,,}" in
      p)
        copy_file "$repo_file" "$inst_file"
        printf "  ${C_GREEN}✓ pushed${C_RESET} %s → install\n" "$name"
        actions_taken+=("pushed instruction: $name")
        ;;
      u)
        copy_file "$inst_file" "$repo_file"
        printf "  ${C_GREEN}✓ pulled${C_RESET} %s → repo\n" "$name"
        actions_taken+=("pulled instruction: $name")
        ;;
      s)
        printf "  ${C_YELLOW}⊘ skipped${C_RESET} %s\n" "$name"
        actions_taken+=("skipped instruction: $name")
        ;;
    esac
  done

  echo
  echo "  ${SEPARATOR:0:50}"
  echo "  Sync complete. Actions taken: ${#actions_taken[@]}"
  for a in "${actions_taken[@]:-}"; do
    [ -n "$a" ] && echo "    • $a"
  done
  echo
}

# ---------------------------------------------------------------------------
# Entrypoint — parse [command] [--all] [-h|--help]
# ---------------------------------------------------------------------------
CMD="${1:-status}"
OPT_ALL=""
for arg in "$@"; do
  [ "$arg" = "--all" ] && OPT_ALL="all"
done

case "$CMD" in
  -h|--help)  usage; exit 0 ;;
  status)     cmd_status ;;
  sync)       cmd_sync "$OPT_ALL" ;;
  *)
    echo -e "${C_RED}Unknown command: $CMD${C_RESET}" >&2
    usage >&2
    exit 2
    ;;
esac

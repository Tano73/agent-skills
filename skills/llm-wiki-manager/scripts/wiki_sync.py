"""Collect implementation changes since the last wiki sync marker.

Deterministic helper for the SYNC workflow (see references/sync.md). It gathers
the git signal (commits + changed file paths since the last processed commit) so
the agent only does the semantic mapping code->wiki pages, without re-running
git plumbing by hand.

Public interface:
    wiki_sync.py <wiki-root> [--since <ref|date|N>] [--write-marker]
                 [--json] [--max-commits N]

Marker file: <wiki-root>/wiki/.sync-marker holds the SHA of the last processed
commit. A run with --write-marker records HEAD so the next run starts there.

Exit codes:
    0  ok
    1  no git repo or no commits (informational, not an agent error)
    2  usage error
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Repo-root-wide directories that never carry the implementation signal. The
# wiki bundle paths (raw/, wiki/) are NOT here: they are added dynamically from
# the wiki root (see wiki_excludes), so a bundle under <repo>/knowledge/ hides
# knowledge/raw and knowledge/wiki, not a nonexistent repo-root wiki/raw.
GLOBAL_EXCLUDED_PREFIXES = (
    ".walden/",
    ".git/",
    "docs/",
    ".github/",
)

MARKER_REL = "wiki/.sync-marker"
DEFAULT_SINCE = "HEAD~5"
MAX_COMMITS_DEFAULT = 50
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def run_git(cwd, args):
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True
    )


def git_output(cwd, args):
    p = run_git(cwd, args)
    if p.returncode != 0:
        return None
    return p.stdout.strip()


def find_repo(wiki_root):
    p = run_git(wiki_root, ["rev-parse", "--show-toplevel"])
    if p.returncode != 0:
        return None
    return Path(p.stdout.strip())


def resolve_base(repo, since):
    """Return (base_commit, display_since) for a --since value.

    base_commit is usable in `git diff <base> HEAD` and `git log <base>..HEAD`.
    For an ISO date the base is the parent of the oldest commit on/after that
    date (the empty tree when it is the root commit). Raises SystemExit(2) for
    an unresolvable ref so a bad value is a clear error, not a silent 0."""
    if DATE_RE.match(since):
        out = git_output(
            repo, ["rev-list", "--reverse", "--since=" + since + " 00:00:00", "HEAD"]
        )
        if not out:
            return None, since
        first = out.splitlines()[0]
        parent = git_output(repo, ["rev-parse", first + "^"])
        base = parent if parent else EMPTY_TREE
        return base, since
    p = run_git(repo, ["rev-parse", "--verify", "--quiet", since + "^{commit}"])
    if p.returncode != 0 or not p.stdout.strip():
        print(
            f"ERROR: cannot resolve --since {since!r} to a commit in {repo}.",
            file=sys.stderr,
        )
        sys.exit(2)
    return since, since


def wiki_excludes(repo, wiki_root):
    """Repo-relative prefixes to hide from the implementation signal.

    The wiki bundle's own content is <wiki_root>/raw and <wiki_root>/wiki.
    Exclude those two relative to the repo (so a wiki under <repo>/knowledge/
    hides knowledge/raw and knowledge/wiki), plus the repo-wide dirs in
    GLOBAL_EXCLUDED_PREFIXES. Falls back to the global set when the wiki root
    is outside the repo.
    """
    excluded = list(GLOBAL_EXCLUDED_PREFIXES)
    try:
        rel = wiki_root.resolve().relative_to(repo)
    except ValueError:
        return tuple(excluded)
    if str(rel) == ".":
        excluded += ("wiki/", "raw/")
    else:
        excluded += (f"{rel}/wiki/", f"{rel}/raw/")
    return tuple(excluded)


def changed_paths(repo, base, head, excluded):
    """List changed file paths between `since` and HEAD, filtered to code/doc
    paths that matter for the wiki (wiki bundle, walden and docs excluded)."""
    diff = git_output(repo, ["diff", "--name-only", base, head])
    if diff is None:
        return []
    paths = []
    for line in diff.splitlines():
        rel = line.strip()
        if not rel:
            continue
        if any(rel.startswith(prefix) for prefix in excluded):
            continue
        paths.append(rel)
    return sorted(set(paths))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="Exit codes: 0 ok, 1 no git repo / no commits, 2 usage error.",
    )
    parser.add_argument("wiki_root", help="path to the wiki root (OKF bundle)")
    parser.add_argument(
        "--since",
        metavar="REF|DATE|N",
        help="override the marker: git ref, ISO date, or integer N meaning HEAD~N",
    )
    parser.add_argument(
        "--write-marker",
        action="store_true",
        help="record HEAD as the last processed commit in wiki/.sync-marker",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--max-commits", type=int, default=MAX_COMMITS_DEFAULT)
    args = parser.parse_args(argv)

    root = Path(args.wiki_root).expanduser()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")

    repo = find_repo(root)
    if repo is None:
        print("INFO: no git repository found (checked up the tree from %s)." % root)
        print("INFO: SYNC needs a git repo; fall back to manual INGEST.")
        return 1

    excluded = wiki_excludes(repo, root)

    head = git_output(repo, ["rev-parse", "HEAD"])
    if not head:
        print("INFO: git repository has no commits yet; nothing to sync.")
        return 1

    marker_path = root / MARKER_REL

    since_arg = args.since
    if since_arg and since_arg.isdigit():
        since_arg = "HEAD~" + since_arg

    marker_text = marker_path.read_text().strip() if marker_path.exists() else ""
    if since_arg:
        source_kind = "--since override"
    elif marker_text:
        source_kind = "marker"
    else:
        source_kind = "no marker, default " + DEFAULT_SINCE
    since = since_arg or (marker_text if marker_text else DEFAULT_SINCE)

    if since != DEFAULT_SINCE:
        base, _ = resolve_base(repo, since)
    else:
        # Default baseline HEAD~5, but repos with fewer than 6 commits must not
        # error: fall back to HEAD (empty change set) so the baseline step works.
        ok = run_git(repo, ["rev-parse", "--verify", "--quiet", "HEAD~5^{commit}"])
        base = DEFAULT_SINCE if ok.returncode == 0 else head
    if base is None:
        # --since date before any commit: nothing changed yet, not an error.
        base = head

    commits = []
    log_out = git_output(
        repo, ["log", f"{base}..HEAD", "--pretty=%h|%ad|%s", "--date=short"]
    )
    if log_out:
        for line in log_out.splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({"sha": parts[0], "date": parts[1], "subject": parts[2]})
                if len(commits) >= args.max_commits:
                    break

    files = changed_paths(repo, base, head, excluded)

    stats = git_output(repo, ["rev-list", "--count", f"{base}..HEAD"])
    total_commits = int(stats) if stats and stats.isdigit() else len(commits)

    if args.write_marker:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(head + "\n")
        marker_written = True
    else:
        marker_written = False

    result = {
        "repo": str(repo),
        "wiki_root": str(root),
        "since": since,
        "since_source": source_kind,
        "head": head,
        "total_commits": total_commits,
        "commits": commits[: args.max_commits],
        "changed_files": files,
        "marker_written": marker_written,
        "marker_path": str(marker_path),
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"repo          : {result['repo']}")
        print(
            f"since         : {since}  ({result['since_source']})"
            "  [--write-marker to record HEAD]"
        )
        print(f"head          : {head}")
        print(f"commits       : {total_commits} since {since}")
        for c in result["commits"]:
            print(f"  {c['sha']}  {c['date']}  {c['subject']}")
        print(f"changed files : {len(files)} ({', '.join(excluded)} excluded)")
        for f in files:
            print(f"  {f}")
        if marker_written:
            print(f"marker        : written → {marker_path}")
        else:
            print(f"marker        : {marker_path} (not written)")

        if not args.since and not marker_path.exists():
            print()
            print("NOTE: no marker yet. Establish a baseline with --write-marker and stop;")
            print("      only then does the next run report the real implementation changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
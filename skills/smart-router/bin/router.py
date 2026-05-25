#!/usr/bin/env python3
"""
Smart-router control CLI.

Manages session state (enable/disable) and the multi-client tier→slug mapping
in models.json. Designed to be invoked both interactively by humans and
non-interactively by the SKILL.md workflow.

Sub-commands:
    enable                    Enable session routing.
    disable                   Disable session routing.
    status                    Print state + active client + tier mapping.
    detect                    Detect the current CLI client from environment.
    init [--client X] [-y]    Interactive (or scripted) wizard to configure a
                              client's tier→slug mapping.
    show [--client X]         Print the tier mapping for a client.
    use <client>              Switch the active client.
    reset [--client X] [-y]   Remove a client's configuration.
    list-clients              List configured clients and known templates.

State file: ~/.smart-router.state (literal "enabled" or "disabled")
Config file: <skill_dir>/models.json (schema v2, multi-client)

Designed to depend only on the Python stdlib.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Any

STATE_FILE = Path.home() / ".smart-router.state"
SKILL_DIR = Path(__file__).resolve().parent.parent
MODELS_PATH = SKILL_DIR / "models.json"

TIER_ORDER = (
    "analyzer",
    "cheap",
    "balanced",
    "heavy",
    "frontier",
    "code-mid",
    "code-heavy",
)

SCHEMA_KEY = "$schema_version"
CURRENT_SCHEMA = "2"


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def read_state() -> str:
    """Return 'enabled' / 'disabled' / 'corrupt' / 'missing'."""
    if not STATE_FILE.exists():
        return "missing"
    raw = STATE_FILE.read_text(encoding="utf-8").strip().lower()
    if raw in ("enabled", "disabled"):
        return raw
    return "corrupt"


def write_state(value: str) -> None:
    if value not in ("enabled", "disabled"):
        raise ValueError(f"invalid state {value!r}")
    STATE_FILE.write_text(value + "\n", encoding="utf-8")


def load_models() -> dict[str, Any]:
    if not MODELS_PATH.exists():
        return _bootstrap_models()
    try:
        data = json.loads(MODELS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: models.json is corrupt: {exc}") from exc
    return _maybe_migrate(data)


def save_models(data: dict[str, Any]) -> None:
    MODELS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _bootstrap_models() -> dict[str, Any]:
    return {
        SCHEMA_KEY: CURRENT_SCHEMA,
        "active_client": None,
        "clients": {},
        "tier_semantics": {},
        "known_clients": {
            "generic": {
                "display_name": "Generic / unknown",
                "env_markers": [],
                "default_slugs": [],
                "default_tier_mapping": {},
            }
        },
    }


def _maybe_migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate schema v1 (single-config) to v2 (multi-client) in memory."""
    if str(data.get(SCHEMA_KEY, "1")) == CURRENT_SCHEMA:
        return data
    migrated: dict[str, Any] = {
        SCHEMA_KEY: CURRENT_SCHEMA,
        "active_client": "cursor",
        "clients": {
            "cursor": {
                "configured_at": _now(),
                "available_slugs": data.get("available_slugs_hint", []),
                "tiers": data.get("tiers", {}),
                "fallback": data.get("fallback", ""),
            }
        },
        "tier_semantics": data.get("tier_semantics", {}),
        "known_clients": data.get("known_clients", {}),
    }
    print("[info] migrated models.json from schema v1 → v2 (kept old config under clients.cursor)", file=sys.stderr)
    return migrated


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Client detection
# ---------------------------------------------------------------------------

def detect_client(known: dict[str, Any]) -> tuple[str | None, str]:
    """Return (client_id_or_None, reason)."""
    path = os.environ.get("PATH", "")
    for client_id, spec in known.items():
        for env in spec.get("env_markers", []):
            if os.environ.get(env):
                return client_id, f"env var {env}={os.environ[env]!r}"
        for marker in spec.get("path_markers", []):
            if marker in path:
                return client_id, f"PATH contains {marker!r}"
    return None, "no marker matched"


# ---------------------------------------------------------------------------
# Sub-command implementations
# ---------------------------------------------------------------------------

def cmd_enable(_args: argparse.Namespace) -> int:
    write_state("enabled")
    print("✅ Smart Router abilitato per questa sessione.")
    print("   Ogni task verrà analizzato e instradato automaticamente al modello più adatto.")
    return 0


def cmd_disable(_args: argparse.Namespace) -> int:
    write_state("disabled")
    print("⏸️  Smart Router disabilitato.")
    print("   I task verranno eseguiti con il modello di default.")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    state = read_state()
    label = {
        "enabled":  "🔍 Smart Router: ATTIVO",
        "disabled": "🔍 Smart Router: DISATTIVO",
        "missing":  "🔍 Smart Router: DISATTIVO (state file assente)",
        "corrupt":  "⚠️  Smart Router: STATO CORROTTO (verrà trattato come DISATTIVO)",
    }[state]
    print(label)

    data = load_models()
    active = data.get("active_client")
    print(f"\nClient attivo: {active!r}")
    if active and active in data.get("clients", {}):
        client = data["clients"][active]
        print(f"  configured_at  : {client.get('configured_at')}")
        print(f"  fallback       : {client.get('fallback')}")
        print(f"  available_slugs: {client.get('available_slugs', [])}")
        print("  tiers:")
        for tier in TIER_ORDER:
            slug = client.get("tiers", {}).get(tier, "—")
            print(f"    {tier:11s} → {slug}")
    else:
        print("  (nessuna configurazione per il client attivo — esegui `init`)")

    other = [c for c in data.get("clients", {}) if c != active]
    if other:
        print(f"\nAltri client configurati: {other}")
    return 0


def cmd_detect(_args: argparse.Namespace) -> int:
    data = load_models()
    client_id, reason = detect_client(data.get("known_clients", {}))
    if client_id is None:
        print(f"❓ Nessun client rilevato automaticamente ({reason}).")
        print("   Esegui `init --client <name>` per configurare manualmente.")
        return 1
    print(f"🔎 Client rilevato: {client_id} ({reason})")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    data = load_models()
    target = args.client or data.get("active_client")
    if not target:
        print("ERROR: nessun client specificato e nessun client attivo.", file=sys.stderr)
        return 2
    client = data.get("clients", {}).get(target)
    if not client:
        print(f"ERROR: client {target!r} non configurato.", file=sys.stderr)
        return 2
    print(f"--- {target} ---")
    print(json.dumps(client, indent=2, ensure_ascii=False))
    return 0


def cmd_use(args: argparse.Namespace) -> int:
    data = load_models()
    if args.client not in data.get("clients", {}):
        print(f"ERROR: client {args.client!r} non configurato. Esegui prima `init --client {args.client}`.", file=sys.stderr)
        return 2
    data["active_client"] = args.client
    save_models(data)
    print(f"✅ Client attivo cambiato in: {args.client}")
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    data = load_models()
    target = args.client or data.get("active_client")
    if not target:
        print("ERROR: nessun client specificato e nessun client attivo.", file=sys.stderr)
        return 2
    if target not in data.get("clients", {}):
        print(f"ERROR: client {target!r} non configurato.", file=sys.stderr)
        return 2
    if not args.yes and sys.stdin.isatty():
        ans = input(f"Rimuovere configurazione di {target!r}? [y/N]: ").strip().lower()
        if ans not in ("y", "yes", "s", "si", "sì"):
            print("Annullato.")
            return 0
    del data["clients"][target]
    if data.get("active_client") == target:
        remaining = list(data.get("clients", {}).keys())
        data["active_client"] = remaining[0] if remaining else None
        if data["active_client"]:
            print(f"[info] active_client → {data['active_client']!r}")
    save_models(data)
    print(f"🗑️  Configurazione di {target!r} rimossa.")
    return 0


def cmd_list_clients(_args: argparse.Namespace) -> int:
    data = load_models()
    active = data.get("active_client")
    configured = data.get("clients", {})
    known = data.get("known_clients", {})

    print("CONFIGURATI:")
    if not configured:
        print("  (nessuno)")
    for cid in configured:
        marker = "★" if cid == active else " "
        cfg = configured[cid]
        print(f"  {marker} {cid:14s} (slugs: {len(cfg.get('available_slugs', []))}, configured_at: {cfg.get('configured_at')})")

    print("\nTEMPLATE NOTI:")
    for cid, spec in known.items():
        print(f"  • {cid:14s} {spec.get('display_name', '')}")
    return 0


def cmd_help(_args: argparse.Namespace) -> int:
    rows = [
        ("enable / attiva / abilita / on", "bin/router.py enable", "Turn on session routing"),
        ("disable / disattiva / disabilita / off", "bin/router.py disable", "Turn off session routing"),
        ("status / stato", "bin/router.py status", "Show state, active client, and tier mapping"),
        ("detect / rileva", "bin/router.py detect", "Detect the current CLI client"),
        ("init / inizializza / setup / configura", "bin/router.py init [--client X]", "Configure a client's tier-to-slug mapping"),
        ("show / mostra", "bin/router.py show [--client X]", "Print the client's mapping"),
        ("use / usa / switch", "bin/router.py use <client>", "Switch the active client"),
        ("reset / rimuovi config", "bin/router.py reset [--client X]", "Remove a client's configuration"),
        ("list-clients / lista client", "bin/router.py list-clients", "List configured clients and known templates"),
        ("help / ? / aiuto", "bin/router.py help", "Show all available commands"),
    ]
    headers = ("Verb aliases", "CLI sub-command", "Description")
    widths = [
        max(len(headers[0]), *(len(r[0]) for r in rows)),
        max(len(headers[1]), *(len(r[1]) for r in rows)),
        max(len(headers[2]), *(len(r[2]) for r in rows)),
    ]

    def fmt(cols: tuple[str, str, str]) -> str:
        return f"{cols[0]:<{widths[0]}}  {cols[1]:<{widths[1]}}  {cols[2]}"

    sep = f"{'-' * widths[0]}  {'-' * widths[1]}  {'-' * widths[2]}"
    print(fmt(headers))
    print(sep)
    for row in rows:
        print(fmt(row))
    return 0


# ---------------------------------------------------------------------------
# `init` wizard
# ---------------------------------------------------------------------------

def _resolve_client_id(args: argparse.Namespace, known: dict[str, Any]) -> str:
    if args.client:
        return args.client
    detected, reason = detect_client(known)
    if detected and _confirm(args, f"Client rilevato: {detected} ({reason}). Usarlo?", default=True):
        return detected
    return _prompt(
        args,
        "Inserisci client id (es. cursor, claude-code, codex-cli, generic): ",
        default=detected or "generic",
    )


def _collect_slugs(args: argparse.Namespace, client_id: str, existing: dict[str, Any], template: dict[str, Any]) -> list[str]:
    default_slugs = existing.get("available_slugs") or template.get("default_slugs") or []
    if args.slugs is not None:
        return [s.strip() for s in args.slugs.split(",") if s.strip()]
    if default_slugs and _confirm(
        args,
        f"Usare gli slug di default per {client_id}?\n  {default_slugs}\nConferma",
        default=True,
    ):
        return list(default_slugs)
    raw = _prompt(args, "Inserisci gli slug disponibili (separati da virgola): ")
    return [s.strip() for s in raw.split(",") if s.strip()]


def _collect_tier_mapping(args: argparse.Namespace, client_id: str, slugs: list[str], existing: dict[str, Any], template: dict[str, Any]) -> dict[str, str]:
    default_tiers = existing.get("tiers") or template.get("default_tier_mapping") or {}
    chosen: dict[str, str] = {}
    print(f"\nMapping tier → slug per {client_id} (Invio per accettare il default):")
    for tier in TIER_ORDER:
        proposal = default_tiers.get(tier) or _first_compatible(slugs, default_tiers.get(tier))
        if proposal not in slugs:
            proposal = slugs[0]
        chosen[tier] = _prompt(args, f"  {tier:11s} [{proposal}]: ", default=proposal)
        if chosen[tier] not in slugs:
            print(f"  [warn] {chosen[tier]!r} non è nella lista degli slug disponibili.", file=sys.stderr)
    return chosen


def cmd_init(args: argparse.Namespace) -> int:
    data = load_models()
    known = data.get("known_clients", {})

    client_id = _resolve_client_id(args, known)
    template = known.get(client_id, {})
    existing = data.get("clients", {}).get(client_id, {})

    slugs = _collect_slugs(args, client_id, existing, template)
    if not slugs:
        print("ERROR: nessuno slug disponibile, impossibile configurare.", file=sys.stderr)
        return 2

    chosen = _collect_tier_mapping(args, client_id, slugs, existing, template)
    fallback_default = existing.get("fallback") or chosen.get("heavy") or slugs[0]
    fallback = _prompt(
        args,
        f"\nFallback slug (per errori di routing) [{fallback_default}]: ",
        default=fallback_default,
    )

    data["clients"][client_id] = {
        "configured_at": _now(),
        "available_slugs": slugs,
        "tiers": chosen,
        "fallback": fallback,
    }
    if not data.get("active_client") or args.set_active:
        data["active_client"] = client_id
    save_models(data)
    print(f"\n✅ Configurazione salvata in {MODELS_PATH}")
    print(f"   Client attivo: {data['active_client']}")
    return 0


def _first_compatible(slugs: list[str], proposal: str | None) -> str | None:
    if proposal and proposal in slugs:
        return proposal
    return slugs[0] if slugs else None


def _confirm(args: argparse.Namespace, msg: str, default: bool = True) -> bool:
    if args.yes:
        return True
    if not sys.stdin.isatty():
        return default
    suffix = " [Y/n]: " if default else " [y/N]: "
    ans = input(msg + suffix).strip().lower()
    if not ans:
        return default
    return ans in ("y", "yes", "s", "si", "sì")


def _prompt(args: argparse.Namespace, msg: str, default: str | None = None) -> str:
    if args.yes:
        if default is not None:
            return default
        print(f"ERROR: --yes specified but no default available for prompt: {msg!r}", file=sys.stderr)
        sys.exit(2)
    if not sys.stdin.isatty():
        if default is not None:
            return default
        print(f"ERROR: stdin not a tty and no default for prompt: {msg!r}", file=sys.stderr)
        sys.exit(2)
    ans = input(msg).strip()
    return ans or (default or "")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="router", description="Smart-router control CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("enable",  help="Enable session routing")
    sub.add_parser("disable", help="Disable session routing")
    sub.add_parser("status",  help="Show state + active client + mapping")
    sub.add_parser("detect",  help="Detect current CLI client from environment")
    sub.add_parser("list-clients", help="List configured and known clients")
    sub.add_parser("help", aliases=["?"], help="Show all available commands")

    p_show = sub.add_parser("show", help="Print a client's mapping")
    p_show.add_argument("--client", help="Client id (default: active)")

    p_use = sub.add_parser("use", help="Switch active client")
    p_use.add_argument("client", help="Client id to activate")

    p_reset = sub.add_parser("reset", help="Remove a client's configuration")
    p_reset.add_argument("--client", help="Client id (default: active)")
    p_reset.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    p_init = sub.add_parser("init", help="Configure a client's mapping (interactive)")
    p_init.add_argument("--client", help="Client id (default: autodetect)")
    p_init.add_argument("--slugs", help="Comma-separated list of available slugs (skip prompt)")
    p_init.add_argument("--set-active", action="store_true", help="Make this client the active one even if another is set")
    p_init.add_argument("-y", "--yes", action="store_true", help="Accept all defaults without prompting (non-interactive)")
    return p


HANDLERS = {
    "enable":       cmd_enable,
    "disable":      cmd_disable,
    "status":       cmd_status,
    "detect":       cmd_detect,
    "show":         cmd_show,
    "use":          cmd_use,
    "reset":        cmd_reset,
    "list-clients": cmd_list_clients,
    "help":         cmd_help,
    "?":            cmd_help,
    "init":         cmd_init,
}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handler = HANDLERS[args.cmd]
    if not hasattr(args, "yes"):
        args.yes = False
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Inspect the local environment and pick the best MinerU backend.

MinerU can run in three very different ways and the right one depends entirely
on the hardware and on whether an OpenAI-compatible VLM server is reachable.
Getting this wrong wastes a lot of time (a CPU-only machine trying to load a
VLM engine will either fail or crawl), so detection is done once, here, and the
result is reused by mineru_convert.py.

Usage:
    mineru_env.py check   [--server-url URL] [--venv PATH] [--json]
    mineru_env.py install [--profile auto|client|pipeline|gpu]
                          [--server-url URL] [--venv PATH] [--dry-run]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_VENV = Path.home() / ".mineru-venv"
SERVER_URL_ENV_VARS = ("MINERU_SERVER_URL", "MINERU_VLM_SERVER_URL")

# Each profile installs only what its backend actually needs. The bare `mineru`
# package is a few MB; the GPU profile pulls vllm and torch (several GB).
INSTALL_PROFILES = {
    "client": ["mineru"],
    "pipeline": ["mineru[pipeline]"],
    "gpu": ["mineru[core,vllm]"],
}

BACKEND_FOR_PROFILE = {
    "client": "vlm-http-client",
    "pipeline": "pipeline",
    "gpu": "hybrid-auto-engine",
}


def detect_gpu():
    """Return the accelerator MinerU could use for local VLM inference."""
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            out = subprocess.run(
                [nvidia_smi, "--query-gpu=name,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=15, check=True,
            ).stdout.strip()
        except (subprocess.SubprocessError, OSError) as exc:
            return {"kind": "none", "detail": f"nvidia-smi failed: {exc}", "vram_gb": 0}
        if out:
            name, _, mem = out.splitlines()[0].partition(",")
            try:
                vram_gb = round(int(mem.strip()) / 1024, 1)
            except ValueError:
                vram_gb = 0
            return {"kind": "cuda", "detail": f"{name.strip()} ({vram_gb} GB VRAM)",
                    "vram_gb": vram_gb}

    if sys.platform == "darwin":
        machine = os.uname().machine
        if machine == "arm64":
            return {"kind": "mps", "detail": "Apple Silicon (MPS)", "vram_gb": 0}

    return {"kind": "none", "detail": "no CUDA GPU or Apple Silicon detected", "vram_gb": 0}


def probe_server(url, timeout=5):
    """Check whether an OpenAI-compatible VLM server answers at `url`."""
    if not url:
        return {"url": None, "reachable": False, "detail": "no server URL configured"}
    endpoint = url.rstrip("/") + "/v1/models"
    try:
        with urllib.request.urlopen(endpoint, timeout=timeout) as resp:
            reachable = 200 <= resp.status < 300
            detail = f"HTTP {resp.status} from {endpoint}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"url": url, "reachable": False, "detail": f"{endpoint} unreachable: {exc}"}
    return {"url": url, "reachable": reachable, "detail": detail}


def resolve_server_url(explicit=None):
    if explicit:
        return explicit
    for var in SERVER_URL_ENV_VARS:
        value = os.environ.get(var)
        if value:
            return value
    return None


def find_mineru(venv=DEFAULT_VENV):
    """Prefer the managed venv over a system-wide install, then fall back to PATH."""
    candidate = Path(venv) / "bin" / "mineru"
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return shutil.which("mineru")


def mineru_version(executable):
    if not executable:
        return None
    try:
        out = subprocess.run([executable, "--version"], capture_output=True,
                             text=True, timeout=60)
    except (subprocess.SubprocessError, OSError):
        return None
    return (out.stdout or out.stderr).strip() or None


def inspect(server_url=None, venv=DEFAULT_VENV):
    gpu = detect_gpu()
    server = probe_server(resolve_server_url(server_url))
    executable = find_mineru(venv)

    # A remote server wins over local hardware: it runs MinerU2.5-Pro at full
    # speed and costs the client machine nothing.
    if server["reachable"]:
        profile, reason = "client", (
            f"remote VLM server reachable ({server['url']}) — runs MinerU2.5-Pro remotely"
        )
    elif gpu["kind"] == "cuda" and gpu["vram_gb"] >= 8:
        profile, reason = "gpu", (
            f"local GPU usable for MinerU2.5-Pro: {gpu['detail']}"
        )
    elif gpu["kind"] == "mps":
        profile, reason = "gpu", "Apple Silicon can run MinerU2.5-Pro locally via mlx"
    else:
        profile, reason = "pipeline", (
            f"{gpu['detail']} and no reachable VLM server — falling back to the CPU "
            "pipeline backend, which does NOT use the MinerU2.5-Pro VLM"
        )

    return {
        "python": sys.version.split()[0],
        "venv": str(venv),
        "mineru_executable": executable,
        "mineru_version": mineru_version(executable),
        "mineru_installed": executable is not None,
        "gpu": gpu,
        "server": server,
        "recommended_profile": profile,
        "recommended_backend": BACKEND_FOR_PROFILE[profile],
        "uses_mineru25pro": profile != "pipeline",
        "reason": reason,
        "install_packages": INSTALL_PROFILES[profile],
    }


def install(profile, venv=DEFAULT_VENV, dry_run=False, server_url=None):
    if profile == "auto":
        profile = inspect(server_url=server_url, venv=venv)["recommended_profile"]
    if profile not in INSTALL_PROFILES:
        raise SystemExit(f"unknown profile: {profile}")

    venv = Path(venv)
    packages = INSTALL_PROFILES[profile]
    pip = venv / "bin" / "pip"

    steps = []
    if not venv.exists():
        steps.append([sys.executable, "-m", "venv", str(venv)])
    steps.append([str(pip), "install", "--upgrade", "pip"])
    steps.append([str(pip), "install", "--upgrade", *packages])

    print(f"Profile: {profile}  ->  packages: {' '.join(packages)}", file=sys.stderr)
    for step in steps:
        print("  $ " + " ".join(step), file=sys.stderr)
    if dry_run:
        return {"profile": profile, "venv": str(venv), "dry_run": True, "steps": steps}

    for step in steps:
        subprocess.run(step, check=True)

    return {"profile": profile, "venv": str(venv), "dry_run": False,
            "mineru_executable": find_mineru(venv)}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="report environment and recommended backend")
    check.add_argument("--server-url")
    check.add_argument("--venv", default=str(DEFAULT_VENV))
    check.add_argument("--json", action="store_true")

    inst = sub.add_parser("install", help="create the venv and install MinerU")
    inst.add_argument("--profile", default="auto",
                      choices=["auto", "client", "pipeline", "gpu"])
    inst.add_argument("--server-url")
    inst.add_argument("--venv", default=str(DEFAULT_VENV))
    inst.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if args.command == "check":
        info = inspect(server_url=args.server_url, venv=Path(args.venv))
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            print(f"Python:            {info['python']}")
            print(f"MinerU:            {info['mineru_version'] or 'not installed'}")
            print(f"Executable:        {info['mineru_executable'] or '-'}")
            print(f"GPU:               {info['gpu']['detail']}")
            print(f"VLM server:        {info['server']['detail']}")
            print(f"Backend:           {info['recommended_backend']}")
            print(f"Uses MinerU2.5-Pro: {'yes' if info['uses_mineru25pro'] else 'no'}")
            print(f"Reason:            {info['reason']}")
            if not info["mineru_installed"]:
                print(f"Install with:      pip install {' '.join(info['install_packages'])}")
        return 0

    result = install(args.profile, Path(args.venv), args.dry_run, args.server_url)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

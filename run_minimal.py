#!/usr/bin/env python3
"""
Start the minimal Streamlit dashboard.

Usage (from repo root):
    python run_minimal.py
    python run_minimal.py -- --server.port 8502
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    os.chdir(root)
    os.environ["PYTHONUNBUFFERED"] = "1"
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(line_buffering=True)
            except OSError:
                pass
    app = root / "dashboard" / "minimal_app.py"
    print("Starting minimal Streamlit dashboard...", flush=True)
    extra = []
    if sys.argv[1:] and sys.argv[1] == "--":
        extra = sys.argv[2:]
    elif sys.argv[1:]:
        extra = sys.argv[1:]
    cmd = [
        sys.executable,
        "-u",
        "-m",
        "streamlit",
        "run",
        str(app),
        *extra,
    ]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()

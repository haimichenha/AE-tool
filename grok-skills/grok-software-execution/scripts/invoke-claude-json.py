#!/usr/bin/env python3
"""Run the Windows Claude CLI from a JSON argument envelope without shell parsing."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True)
    ns = ap.parse_args()
    try:
        data = json.loads(Path(ns.request).read_text(encoding="utf-8"))
        command = str(data["command"])
        args = [str(value) for value in data["args"]]
        completed = subprocess.run(
            [command, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            check=False,
        )
        result = {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except Exception as exc:
        result = {"returncode": 127, "stdout": "", "stderr": f"bridge error: {exc}"}
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

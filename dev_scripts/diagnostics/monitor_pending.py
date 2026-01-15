#!/usr/bin/env python3
import argparse
import os
import sys
import json
from datetime import datetime, timezone

# Ensure we can import the project's app context if needed
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

CHECK_SCRIPT = os.path.join(BASE_DIR, 'dev_scripts', 'diagnostics', 'check_pending_count.py')


def run_check():
    """Execute the existing check script and return parsed counts dict.
    We import the script as a module-like run by executing and capturing stdout.
    """
    import subprocess

    try:
        proc = subprocess.run(
            [sys.executable, CHECK_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=BASE_DIR,
            timeout=30,
        )
    except Exception as e:
        print(f"monitor_pending: failed to run check script: {e}", file=sys.stderr)
        return None, 3

    if proc.returncode != 0:
        print(
            f"monitor_pending: check script failed rc={proc.returncode}: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None, 3

    # Attempt to parse JSON object from stdout
    out = proc.stdout.strip()
    # The check script prints a dict-like structure; support both JSON and repr
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        try:
            # Very simple eval guard: only allow dict/str/int keys
            data = eval(out, {"__builtins__": {}}, {})  # noqa: S307 (controlled input)
            if not isinstance(data, dict):
                raise ValueError("Parsed output is not a dict")
        except Exception as e:
            print(f"monitor_pending: could not parse output: {e}; raw: {out[:200]}", file=sys.stderr)
            return None, 3

    return data, 0


def main():
    parser = argparse.ArgumentParser(description="Monitor pending queue size and exit non-zero on threshold")
    parser.add_argument("--threshold", type=int, default=int(os.environ.get("PENDING_THRESHOLD", 50)), help="Pending threshold to alert on")
    parser.add_argument("--quiet", action="store_true", help="Only emit output on failure")
    args = parser.parse_args()

    data, rc = run_check()
    if rc != 0 or data is None:
        # Unhealthy if we can't even fetch metrics
        sys.exit(3)

    pending = int(data.get("pending", 0))
    processed = int(data.get("processed", 0))
    failed = int(data.get("failed", 0))

    ts = datetime.now(timezone.utc).isoformat()
    msg = f"[{ts}] pending={pending} processed={processed} failed={failed} threshold={args.threshold}"

    if pending > args.threshold:
        if not args.quiet:
            print("ALERT:", msg)
        # Exit code 2 = critical
        sys.exit(2)

    if not args.quiet:
        print("OK:", msg)
    sys.exit(0)


if __name__ == "__main__":
    main()

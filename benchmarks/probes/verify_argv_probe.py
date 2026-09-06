"""Durable CI probe to verify J2 CLI argument forwarding behavior (TASK T005-B1).

Tests:
1. `j2 run FILE.j2 arg1 arg2`
   - In J2 0.1.0, proc.argv() drops all trailing application arguments (len == 1).
2. `j2 [capabilities] FILE.j2 arg1 arg2`
   - In J2 0.1.0, proc.argv() forwards all trailing arguments (len == 3: [file, arg1, arg2]).

This probe validates why Baseline A uses `j2 --allow-fs src/main.j2 <corpus> --json`
and prevents accidental regression to the broken `j2 run` argument-dropping form.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

PROBE_DIR = Path(__file__).resolve().parent
PROBE_J2 = PROBE_DIR / "probe_argv.j2"


def run_probe(j2_bin: str = "j2") -> tuple[bool, str]:
    if not shutil.which(j2_bin):
        return True, f"SKIP: J2 executable '{j2_bin}' not found on PATH. Probe skipped for offline environment."

    if not PROBE_J2.is_file():
        return False, f"FAIL: Probe source file not found: {PROBE_J2}"

    # 1. Test `j2 run FILE.j2 foo bar`
    cmd_run = [j2_bin, "run", str(PROBE_J2), "foo", "bar"]
    res_run = subprocess.run(cmd_run, capture_output=True, text=True, check=False)
    out_run = res_run.stdout.strip()

    # 2. Test `j2 --allow-fs FILE.j2 foo bar`
    cmd_bare = [j2_bin, "--allow-fs", str(PROBE_J2), "foo", "bar"]
    res_bare = subprocess.run(cmd_bare, capture_output=True, text=True, check=False)
    out_bare = res_bare.stdout.strip()

    logs: list[str] = [
        "=== J2 CLI Argv Forwarding Probe ===",
        f"Command 1: {' '.join(cmd_run)}",
        f"Exit code: {res_run.returncode}",
        f"Stdout: {out_run}",
        f"Command 2: {' '.join(cmd_bare)}",
        f"Exit code: {res_bare.returncode}",
        f"Stdout: {out_bare}",
    ]

    # Verify Command 1 drops arguments (len == 1)
    run_drops_args = "ARGV_COUNT:1" in out_run and "ARG:foo" not in out_run
    # Verify Command 2 forwards arguments (len == 3, contains foo and bar)
    bare_forwards_args = (
        "ARGV_COUNT:3" in out_bare
        and "ARG:foo" in out_bare
        and "ARG:bar" in out_bare
    )

    if not bare_forwards_args:
        logs.append(
            f"FAIL: Verified capability invocation '{' '.join(cmd_bare)}' did not forward trailing arguments!\n"
            f"Expected ARGV_COUNT:3 with 'ARG:foo' and 'ARG:bar'. Got:\n{out_bare}"
        )
        return False, "\n".join(logs)

    if not run_drops_args:
        logs.append(
            f"NOTE: 'j2 run' behavior has changed: trailing arguments were forwarded (out: {out_run})."
        )
    else:
        logs.append(
            "CONFIRMED: In J2 0.1.0, 'j2 run FILE arg1 arg2' drops arguments (count=1), "
            "while 'j2 --allow-fs FILE arg1 arg2' forwards arguments (count=3). "
            "Baseline A must use the verified capability invocation form."
        )

    return True, "\n".join(logs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe J2 CLI argument forwarding behavior")
    parser.add_argument("--j2-bin", default="j2", help="Path to j2 binary (default: j2)")
    args = parser.parse_args()

    success, message = run_probe(j2_bin=args.j2_bin)
    print(message)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

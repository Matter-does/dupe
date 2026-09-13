"""Entry point for running dupe GUI via `python -m gui`."""

from __future__ import annotations

import argparse
import sys

from gui.adapter import EngineAdapter
from gui.app import DupeApp


def main() -> int:
    parser = argparse.ArgumentParser(description="dupe — Filesystem Intelligence Desktop GUI Shell")
    parser.add_argument("-t", "--target", type=str, default="", help="Initial target directory")
    parser.add_argument(
        "-w",
        "--workload",
        type=str,
        choices=["duplicate", "checksum"],
        default="duplicate",
        help="Initial analysis workload (duplicate or checksum)",
    )
    parser.add_argument("--native-bin", type=str, default=None, help="Path to native compiled dupe binary")
    parser.add_argument("--j2-bin", type=str, default=None, help="Path to J2 compiler/interpreter binary")

    args = parser.parse_args()

    adapter = EngineAdapter(native_bin=args.native_bin, j2_bin=args.j2_bin)
    app = DupeApp(
        adapter=adapter,
        initial_path=args.target,
        initial_workload=args.workload,
    )
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

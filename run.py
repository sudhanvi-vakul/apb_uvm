#!/usr/bin/env python3
"""
APB UVM regression runner for Questa/qrun.

Expected source layout: keep this run.py in the same directory as:
  design.sv, testbench.sv, apb_if.sv, apb_txn.sv, apb_seqr.sv,
  apb_sequence.sv, apb_drv.sv, apb_mon.sv, apb_agent.sv,
  apb_scb.sv, apb_cov.sv, apb_env.sv, apb_test.sv

Usage examples:
  python3 run.py --test smoke_test
  python3 run.py --test random_test --seed 123 --cov
  python3 run.py --all --cov
  python3 run.py --clean
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TESTS = [
    "smoke_test",
    "write_read_test",
    "back2back_test",
    "random_test",
]

# Only compile the real RTL top and TB top. The UVM files are included by testbench.sv.
TOP_COMPILE_FILES = ["design.sv", "testbench.sv"]

REQUIRED_FILES = [
    "design.sv",
    "testbench.sv",
    "apb_if.sv",
    "apb_txn.sv",
    "apb_seqr.sv",
    "apb_sequence.sv",
    "apb_drv.sv",
    "apb_mon.sv",
    "apb_agent.sv",
    "apb_scb.sv",
    "apb_cov.sv",
    "apb_env.sv",
    "apb_test.sv",
]

GENERATED_PATTERNS = [
    "qrun.out",
    "work",
    "reports",
    "transcript",
    "modelsim.ini",
    "*.log",
    "*.vcd",
    "*.wlf",
    "*.ucdb",
    "*.jou",
]


def stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def check_required_files(root: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if missing:
        print("ERROR: Missing required source files:")
        for name in missing:
            print(f"  - {name}")
        print("\nKeep run.py in the same folder as the APB UVM .sv files.")
        sys.exit(2)


def clean(root: Path) -> None:
    print("Cleaning generated simulator outputs...")
    for pattern in GENERATED_PATTERNS:
        for path in root.glob(pattern):
            if path.name == "run.py":
                continue
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                print(f"  removed dir  {path.relative_to(root)}")
            elif path.exists():
                path.unlink()
                print(f"  removed file {path.relative_to(root)}")


def write_do_file(run_dir: Path, coverage: bool) -> Path:
    do_file = run_dir / "run.do"
    lines = [
        "run -all",
    ]
    if coverage:
        lines += [
            "coverage save coverage.ucdb",
            "coverage report -detail -cvg -file coverage.txt",
        ]
    lines += ["quit -f"]
    do_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return do_file


def run_cmd(cmd: list[str], cwd: Path, log_file: Path) -> int:
    print("\nCommand:")
    print(" ".join(cmd))
    print(f"\nRun directory: {cwd}")
    with log_file.open("w", encoding="utf-8", errors="replace") as log:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="")
            log.write(line)
        return proc.wait()


def summarize(log_file: Path, summary_file: Path) -> bool:
    text = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""

    uvm_error = re.search(r"UVM_ERROR\s*:\s*(\d+)", text)
    uvm_fatal = re.search(r"UVM_FATAL\s*:\s*(\d+)", text)
    tool_error = re.findall(r"Errors:\s*(\d+)", text)
    coverage = re.search(r"Coverage\s*=\s*([0-9.]+)%", text)

    uvm_error_count = int(uvm_error.group(1)) if uvm_error else -1
    uvm_fatal_count = int(uvm_fatal.group(1)) if uvm_fatal else -1
    max_tool_errors = max([int(x) for x in tool_error], default=0)

    passed = (
        uvm_error_count == 0
        and uvm_fatal_count == 0
        and max_tool_errors == 0
        and "UVM/REPORT/SERVER" in text
    )

    lines = [
        f"RESULT: {'PASS' if passed else 'FAIL_OR_INCOMPLETE'}",
        f"UVM_ERROR: {uvm_error_count if uvm_error_count >= 0 else 'not found'}",
        f"UVM_FATAL: {uvm_fatal_count if uvm_fatal_count >= 0 else 'not found'}",
        f"Max tool Errors field: {max_tool_errors}",
        f"Coverage: {coverage.group(1) + '%' if coverage else 'not found'}",
        f"Log: {log_file}",
    ]
    summary_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))
    return passed


def run_one(root: Path, test: str, seed: int | None, coverage: bool) -> bool:
    check_required_files(root)

    qrun = shutil.which("qrun")
    if qrun is None:
        print("ERROR: qrun was not found in PATH.")
        print("This project is UVM-based, so use Questa/qrun on Nobel, or load the Questa module first.")
        print("Try: module avail questa   OR   which qrun")
        sys.exit(127)

    if test not in TESTS:
        print(f"ERROR: Unknown test '{test}'. Valid tests: {', '.join(TESTS)}")
        sys.exit(2)

    seed = seed if seed is not None else int(dt.datetime.now().strftime("%H%M%S"))
    run_dir = root / "reports" / f"run_{stamp()}_{test}_seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    do_file = write_do_file(run_dir, coverage)

    src_files = [str(root / f) for f in TOP_COMPILE_FILES]
    cmd = [
        qrun,
        "-batch",
        "-access=rw+/.",
        "-uvmhome", "uvm-1.2",
        "-timescale", "1ns/1ns",
        "-mfcu",
        f"+incdir+{root}",
        *src_files,
        "-voptargs=+acc=npr",
        f"+UVM_TESTNAME={test}",
        f"+ntb_random_seed={seed}",
    ]
    if coverage:
        cmd.append("-coverage")
    cmd += ["-do", str(do_file)]

    log_file = run_dir / "qrun.log"
    ret = run_cmd(cmd, run_dir, log_file)
    passed = summarize(log_file, run_dir / "summary.txt")

    print(f"\nArtifacts saved under: {run_dir}")
    if (run_dir / "dump.vcd").exists():
        print(f"Waveform VCD: {run_dir / 'dump.vcd'}")
    if ret != 0:
        print(f"Simulator returned non-zero exit code: {ret}")
        passed = False
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run APB UVM tests with Questa qrun")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--test", default="smoke_test", help=f"UVM test name. Valid: {', '.join(TESTS)}")
    group.add_argument("--all", action="store_true", help="Run all known UVM tests")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--cov", action="store_true", help="Enable coverage collection and coverage report")
    parser.add_argument("--clean", action="store_true", help="Remove generated simulation outputs and exit")

    args = parser.parse_args()
    root = repo_root()

    if args.clean:
        clean(root)
        return 0

    tests = TESTS if args.all else [args.test]
    overall_pass = True
    for test in tests:
        # If running all, let each test get a different timestamp-derived seed unless user provided one.
        overall_pass = run_one(root, test, args.seed, args.cov) and overall_pass

    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

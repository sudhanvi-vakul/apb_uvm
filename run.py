#!/usr/bin/env python3
"""
APB UVM regression runner for Nobel server.
Compatible with older Python 3 versions.

Usage:
  python3 run.py --clean
  python3 run.py --test smoke_test
  python3 run.py --test random_test --seed 123
  python3 run.py --test random_test --seed 123 --cov
  python3 run.py --all --cov
"""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys


TESTS = [
    "smoke_test",
    "write_read_test",
    "back2back_test",
    "random_test",
]


SOURCE_FILES = [
    "design.sv",
    "testbench.sv",
]


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


GENERATED_ITEMS = [
    "qrun.out",
    "work",
    "reports",
    "transcript",
    "modelsim.ini",
]


GENERATED_EXTENSIONS = [
    ".log",
    ".vcd",
    ".wlf",
    ".ucdb",
    ".jou",
]


def stamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def repo_root():
    return os.path.dirname(os.path.abspath(__file__))


def check_required_files(root):
    missing = []

    for name in REQUIRED_FILES:
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            missing.append(name)

    if missing:
        print("ERROR: Missing required source files:")
        for name in missing:
            print("  - " + name)

        print("")
        print("Keep run.py in the same folder as the APB UVM .sv files.")
        sys.exit(2)


def clean(root):
    print("Cleaning generated simulator outputs...")

    for name in GENERATED_ITEMS:
        path = os.path.join(root, name)

        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
            print("  removed dir  " + name)

        elif os.path.isfile(path):
            os.remove(path)
            print("  removed file " + name)

    for name in os.listdir(root):
        path = os.path.join(root, name)

        if os.path.isfile(path):
            for ext in GENERATED_EXTENSIONS:
                if name.endswith(ext):
                    os.remove(path)
                    print("  removed file " + name)
                    break


def write_do_file(run_dir, coverage):
    do_file = os.path.join(run_dir, "run.do")

    lines = []
    lines.append("run -all")

    if coverage:
        lines.append("coverage save coverage.ucdb")
        lines.append("coverage report -detail -cvg -file coverage.txt")

    lines.append("quit -f")

    with open(do_file, "w") as f:
        f.write("\n".join(lines) + "\n")

    return do_file


def run_cmd(cmd, cwd, log_file):
    print("")
    print("Command:")
    print(" ".join(cmd))
    print("")
    print("Run directory: " + cwd)
    print("")

    with open(log_file, "w") as log:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

        for line in proc.stdout:
            print(line, end="")
            log.write(line)

        return proc.wait()


def summarize(log_file, summary_file):
    if os.path.isfile(log_file):
        with open(log_file, "r", errors="replace") as f:
            text = f.read()
    else:
        text = ""

    uvm_error = re.search(r"UVM_ERROR\s*:\s*(\d+)", text)
    uvm_fatal = re.search(r"UVM_FATAL\s*:\s*(\d+)", text)
    coverage = re.search(r"Coverage\s*=\s*([0-9.]+)%", text)

    tool_error_matches = re.findall(r"Errors:\s*(\d+)", text)

    if uvm_error:
        uvm_error_count = int(uvm_error.group(1))
    else:
        uvm_error_count = -1

    if uvm_fatal:
        uvm_fatal_count = int(uvm_fatal.group(1))
    else:
        uvm_fatal_count = -1

    if tool_error_matches:
        max_tool_errors = max([int(x) for x in tool_error_matches])
    else:
        max_tool_errors = 0

    passed = (
        uvm_error_count == 0 and
        uvm_fatal_count == 0 and
        max_tool_errors == 0
    )

    lines = []
    lines.append("RESULT: " + ("PASS" if passed else "FAIL_OR_INCOMPLETE"))

    if uvm_error_count >= 0:
        lines.append("UVM_ERROR: " + str(uvm_error_count))
    else:
        lines.append("UVM_ERROR: not found")

    if uvm_fatal_count >= 0:
        lines.append("UVM_FATAL: " + str(uvm_fatal_count))
    else:
        lines.append("UVM_FATAL: not found")

    lines.append("Max tool Errors field: " + str(max_tool_errors))

    if coverage:
        lines.append("Coverage: " + coverage.group(1) + "%")
    else:
        lines.append("Coverage: not found")

    lines.append("Log: " + log_file)

    with open(summary_file, "w") as f:
        f.write("\n".join(lines) + "\n")

    print("")
    print("\n".join(lines))

    return passed


def run_one(root, test, seed, coverage):
    check_required_files(root)

    qrun = shutil.which("qrun")

    if qrun is None:
        print("ERROR: qrun was not found in PATH.")
        print("")
        print("This APB project is UVM-based, so it needs Questa qrun, VCS, or Xcelium.")
        print("On Nobel, try loading a simulator module first.")
        print("")
        print("Try:")
        print("  module avail 2>&1 | grep -Ei \"questa|mentor|modelsim|vcs|xcelium|cadence|synopsys\"")
        print("")
        print("Then load the available simulator module.")
        sys.exit(127)

    if test not in TESTS:
        print("ERROR: Unknown test '" + test + "'.")
        print("Valid tests: " + ", ".join(TESTS))
        sys.exit(2)

    if seed is None:
        seed = int(datetime.datetime.now().strftime("%H%M%S"))

    run_name = "run_" + stamp() + "_" + test + "_seed" + str(seed)
    run_dir = os.path.join(root, "reports", run_name)

    os.makedirs(run_dir, exist_ok=True)

    do_file = write_do_file(run_dir, coverage)

    src_files = []
    for src in SOURCE_FILES:
        src_files.append(os.path.join(root, src))

    cmd = [
        qrun,
        "-batch",
        "-access=rw+/.",
        "-uvmhome",
        "uvm-1.2",
        "-timescale",
        "1ns/1ns",
        "-mfcu",
        "+incdir+" + root,
    ]

    cmd.extend(src_files)

    cmd.extend([
        "-voptargs=+acc=npr",
        "+UVM_TESTNAME=" + test,
        "+ntb_random_seed=" + str(seed),
    ])

    if coverage:
        cmd.append("-coverage")

    cmd.extend(["-do", do_file])

    log_file = os.path.join(run_dir, "qrun.log")
    ret = run_cmd(cmd, run_dir, log_file)

    summary_file = os.path.join(run_dir, "summary.txt")
    passed = summarize(log_file, summary_file)

    print("")
    print("Artifacts saved under:")
    print("  " + run_dir)

    if ret != 0:
        print("")
        print("Simulator returned non-zero exit code: " + str(ret))
        passed = False

    return passed


def main():
    parser = argparse.ArgumentParser(description="Run APB UVM tests with Questa qrun")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--test", default="smoke_test")
    group.add_argument("--all", action="store_true")

    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--cov", action="store_true")
    parser.add_argument("--clean", action="store_true")

    args = parser.parse_args()
    root = repo_root()

    if args.clean:
        clean(root)
        return 0

    if args.all:
        tests = TESTS
    else:
        tests = [args.test]

    overall_pass = True

    for test in tests:
        result = run_one(root, test, args.seed, args.cov)

        if not result:
            overall_pass = False

    if overall_pass:
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
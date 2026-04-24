#!/usr/bin/env python3
"""
APB UVM regression runner for the Nobel server.

This script is intentionally written without modern Python-only syntax such as:
  - from __future__ import annotations
  - list[str]
  - int | None
  - pathlib-only flows

It should work on older Python 3 versions commonly found on university servers.

Typical usage:
  python3 run.py --clean
  python3 run.py --test smoke_test
  python3 run.py --test write_read_test --seed 123
  python3 run.py --test random_test --seed 123 --cov
  python3 run.py --all --cov

Simulator usage:
  python3 run.py --sim auto --test smoke_test
  python3 run.py --sim qrun --test smoke_test
  python3 run.py --sim questa --test smoke_test
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


# testbench.sv should include the UVM files.
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
    "vsim.wlf",
]


GENERATED_EXTENSIONS = [
    ".log",
    ".vcd",
    ".wlf",
    ".ucdb",
    ".jou",
    ".pb",
]


def stamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def repo_root():
    return os.path.dirname(os.path.abspath(__file__))


def find_executable(program_name):
    """
    Lightweight replacement for shutil.which.
    This keeps the script friendly to older Python versions.
    """
    paths = os.environ.get("PATH", "").split(os.pathsep)

    for path_dir in paths:
        full_path = os.path.join(path_dir, program_name)

        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path

    return None


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def read_text_file(path):
    if not os.path.isfile(path):
        return ""

    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except TypeError:
        with open(path, "r") as f:
            return f.read()


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

    print("Clean complete.")


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
    print("Log file: " + log_file)
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
    text = read_text_file(log_file)

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

    compile_or_sim_error = False

    fatal_patterns = [
        r"\*\* Error:",
        r"\*\* Fatal:",
        r"Error loading design",
        r"Compilation failed",
        r"Syntax error",
        r"Undefined variable",
        r"Unknown option",
    ]

    for pattern in fatal_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            compile_or_sim_error = True
            break

    passed = (
        uvm_error_count == 0 and
        uvm_fatal_count == 0 and
        max_tool_errors == 0 and
        not compile_or_sim_error
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
    lines.append("Compile or simulator error pattern found: " + str(compile_or_sim_error))

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


def resolve_simulator(sim_choice):
    """
    Returns one of:
      qrun
      questa

    qrun flow uses qrun directly.
    questa flow uses vlog + vsim.
    """

    qrun = find_executable("qrun")
    vlog = find_executable("vlog")
    vsim = find_executable("vsim")

    if sim_choice == "qrun":
        if qrun:
            return "qrun"
        print_simulator_error()
        sys.exit(127)

    if sim_choice == "questa":
        if vlog and vsim:
            return "questa"
        print_simulator_error()
        sys.exit(127)

    if qrun:
        return "qrun"

    if vlog and vsim:
        return "questa"

    print_simulator_error()
    sys.exit(127)


def print_simulator_error():
    print("ERROR: No supported UVM simulator was found in PATH.")
    print("")
    print("This APB project is UVM-based. It needs one of these available:")
    print("  1. Questa qrun")
    print("  2. Questa or ModelSim with vlog and vsim")
    print("")
    print("On Nobel, try checking available modules:")
    print("  module avail 2>&1 | grep -Ei \"questa|mentor|modelsim|vcs|xcelium|cadence|synopsys\"")
    print("")
    print("Then load the available simulator module, for example:")
    print("  module load questa")
    print("")
    print("After loading a module, check:")
    print("  which qrun")
    print("  which vlog")
    print("  which vsim")


def build_qrun_command(root, test, seed, coverage, do_file):
    qrun = find_executable("qrun")

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

    return cmd


def run_questa_flow(root, run_dir, test, seed, coverage, do_file):
    """
    Classic Questa flow for servers where qrun is unavailable:
      vlib work
      vlog -sv ...
      vsim -c ...
    """

    vlib = find_executable("vlib")
    vlog = find_executable("vlog")
    vsim = find_executable("vsim")

    if not vlog or not vsim:
        print_simulator_error()
        sys.exit(127)

    if vlib:
        vlib_log = os.path.join(run_dir, "vlib.log")
        ret = run_cmd([vlib, "work"], run_dir, vlib_log)
        if ret != 0:
            return ret

    src_files = []
    for src in SOURCE_FILES:
        src_files.append(os.path.join(root, src))

    vlog_cmd = [
        vlog,
        "-sv",
        "-mfcu",
        "+acc",
        "+incdir+" + root,
    ]

    if coverage:
        vlog_cmd.append("+cover")

    vlog_cmd.extend(src_files)

    vlog_log = os.path.join(run_dir, "vlog.log")
    ret = run_cmd(vlog_cmd, run_dir, vlog_log)
    if ret != 0:
        return ret

    vsim_cmd = [
        vsim,
        "-c",
        "-voptargs=+acc=npr",
        "+UVM_TESTNAME=" + test,
        "+ntb_random_seed=" + str(seed),
    ]

    if coverage:
        vsim_cmd.append("-coverage")

    vsim_cmd.extend([
        "tb_top",
        "-do",
        do_file,
    ])

    vsim_log = os.path.join(run_dir, "qrun.log")
    ret = run_cmd(vsim_cmd, run_dir, vsim_log)

    return ret


def run_one(root, test, seed, coverage, sim_choice):
    check_required_files(root)

    if test not in TESTS:
        print("ERROR: Unknown test '" + test + "'.")
        print("Valid tests: " + ", ".join(TESTS))
        sys.exit(2)

    if seed is None:
        seed = int(datetime.datetime.now().strftime("%H%M%S"))

    simulator = resolve_simulator(sim_choice)

    run_name = "run_" + stamp() + "_" + test + "_seed" + str(seed)
    run_dir = os.path.join(root, "reports", run_name)
    ensure_dir(run_dir)

    do_file = write_do_file(run_dir, coverage)

    print("")
    print("Selected simulator flow: " + simulator)

    log_file = os.path.join(run_dir, "qrun.log")

    if simulator == "qrun":
        cmd = build_qrun_command(root, test, seed, coverage, do_file)
        ret = run_cmd(cmd, run_dir, log_file)

    elif simulator == "questa":
        ret = run_questa_flow(root, run_dir, test, seed, coverage, do_file)

    else:
        print("Internal error: unsupported simulator flow " + simulator)
        return False

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
    parser = argparse.ArgumentParser(description="Run APB UVM tests on Nobel")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--test", default="smoke_test")
    group.add_argument("--all", action="store_true")

    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--cov", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument(
        "--sim",
        choices=["auto", "qrun", "questa"],
        default="auto",
        help="Simulator flow to use. Default: auto",
    )

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
        result = run_one(root, test, args.seed, args.cov, args.sim)

        if not result:
            overall_pass = False

    if overall_pass:
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
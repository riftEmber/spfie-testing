#!/usr/bin/python3

import subprocess
import os
import sys
import hashlib

POLYBENCH_TAR="polybench-c-4.2.tar.gz"
POLYBENCH_TAR_SHA256="ecf1546d84ff4dc4ff02a8ad4b303ff15c6fd0940fccb37fd9dfb2eb223fe8b3"
POLYBENCH_DIR="polybench-c-4.2"
PROCESSED_SRC_DIR="processed"

def main():
    print(f"Extracting polybench sources from {POLYBENCH_TAR}")
    if os.path.isdir(POLYBENCH_DIR):
        sys.exit(f"Sources directory {POLYBENCH_DIR} already exists, quitting")
    with open(POLYBENCH_TAR, "rb") as f:
        if not hashlib.sha256(f.read()).hexdigest() == POLYBENCH_TAR_SHA256:
            sys.exit(f"Polybench tar file {POLYBENCH_TAR} did not have expected hash")
    run_cmd(f"tar -xzf {POLYBENCH_TAR}")
    print("Processing sources")
    if not os.path.isdir(POLYBENCH_DIR):
        sys.exit(f"Sources directory {POLYBENCH_DIR} does not exist, quitting")
    os.chdir(POLYBENCH_DIR)
    os.mkdir(PROCESSED_SRC_DIR)
    with open("utilities/benchmark_list") as benchmark_list_f:
        benchmark_list = benchmark_list_f.readlines()
        for benchmark in benchmark_list:
            kernel_name = benchmark.split('/')[-1].rstrip()
            print(f"Processing kernel {kernel_name}")

def run_cmd(command):
    subprocess.run(command.split())

main()

#!/usr/bin/python3

import subprocess
import os
import sys
import hashlib

DEBUG = False

POLYBENCH_TAR = "polybench-c-4.2.tar.gz"
POLYBENCH_TAR_SHA256 = "ecf1546d84ff4dc4ff02a8ad4b303ff15c6fd0940fccb37fd9dfb2eb223fe8b3"
POLYBENCH_DIR = "polybench-c-4.2"
PROCESSED_SRC_DIR = "processed"
TMP_KERNEL_FILE = r"tmp_kernel.c"


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
    with open("utilities/benchmark_list") as benchmark_list:
        benchmark_list = benchmark_list.readlines()
        num_benchmarks = len(benchmark_list)
        current_benchmark = 0
        failure_count = 0
        for benchmark in benchmark_list:
            current_benchmark += 1
            # kernel_name = benchmark.split('/')[-1].rstrip().removesuffix(".c")
            kernel_name = benchmark.split('/')[-1].rstrip()[:-2]
            kernel_path = '/'.join(benchmark.split('/')[:-1])
            print(f"Processing kernel {current_benchmark}/{num_benchmarks}: '{kernel_name}' in {kernel_path}")

            # generate macro-free benchmark
            run_cmd(f"perl utilities/create_cpped_version.pl {benchmark} -I utilities -DPOLYBENCH_USE_C99_PROTO")
            kernel_function_name = "kernel_" + kernel_name.replace('-', '_')
            print_debug(f"searching for fucntion {kernel_function_name}")
            with open(f"{kernel_path}/{kernel_name}.preproc.c") as preprocessed:
                preprocessed_lines = preprocessed.readlines()
                line_number = 1

                # find beginning of function
                for line in preprocessed_lines:
                    if kernel_function_name in line:
                        break
                    else:
                        line_number += 1
                if line_number >= len(preprocessed_lines):
                    sys.exit(f"Could not find kernel function '{kernel_function_name}'!")
                else:
                    start_line = line_number - 1
                    print_debug(f"found on line {line_number}/{len(preprocessed_lines)}")

                # find end of function
                for line in preprocessed_lines[line_number:]:
                    if line.rstrip() == "}":
                        break
                    else:
                        line_number += 1
                if line_number >= len(preprocessed_lines):
                    sys.exit(f"Could not find end of kernel function '{kernel_function_name}'!")
                else:
                    end_line = line_number + 1
                kernel_snippet_lines = [x for x in preprocessed_lines[start_line:end_line] if "pragma" not in x]
                kernel_snippet = "".join(kernel_snippet_lines)
                print_debug("original: " + kernel_snippet)
                with open(TMP_KERNEL_FILE, "w") as tmp_file:
                    tmp_file.write(kernel_snippet)
                spfie_run_output = subprocess.run(
                    f"../../build/bin/spf-ie {TMP_KERNEL_FILE} --entry-point {kernel_function_name}".split(),
                    capture_output=True)
                # spfie_run_output.check_returncode()
                if spfie_run_output.returncode != 0:
                    print(f"spf-ie run on kernel '{kernel_name}' had exit code of {spfie_run_output.returncode}")
                    print_debug("spf-ie stderr:")
                    print_debug(spfie_run_output.stderr.decode())
                    print(f"skipping kernel {kernel_name}")
                    failure_count += 1
                    # sys.exit()
                    continue
                optimized_snippet = spfie_run_output.stdout.decode()
                print_debug("optimized: " + optimized_snippet)
        print(f"{num_benchmarks} benchmarks processed, {num_benchmarks - failure_count} succeeded, {failure_count} failed")


def run_cmd(command):
    subprocess.run(command.split())


def print_debug(msg):
    if DEBUG:
        print("debug: " + msg)


main()

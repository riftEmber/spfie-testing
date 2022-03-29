#!/usr/bin/python3

import subprocess
import os
import sys
import io
import hashlib

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
        for benchmark in benchmark_list:
            # kernel_name = benchmark.split('/')[-1].rstrip().removesuffix(".c")
            kernel_name = benchmark.split('/')[-1].rstrip()[:-2]
            kernel_path = '/'.join(benchmark.split('/')[:-1])
            print(f"Processing kernel '{kernel_name}' in {kernel_path}")

            # generate macro-free benchmark
            run_cmd(f"perl utilities/create_cpped_version.pl {benchmark} -I utilities -DPOLYBENCH_USE_C99_PROTO")
            kernel_function_name = "kernel_" + kernel_name.replace('-', '_')
            print(f"searching for fucntion {kernel_function_name}")
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
                    print(f"found on line {line_number}/{len(preprocessed_lines)}")

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

                kernel_snippet = "".join(preprocessed_lines[start_line:end_line])
                print("original: " + kernel_snippet)
                with open(TMP_KERNEL_FILE, "w") as tmp_file:
                    tmp_file.write(kernel_snippet)
                spfie_output = subprocess.run(
                    f"../../build/bin/spf-ie {TMP_KERNEL_FILE} --entry-point {kernel_function_name}".split(),
                    capture_output=True)
                optimized_snippet = spfie_output.stderr.decode()
                print("optimized: " + optimized_snippet)


def run_cmd(command):
    subprocess.run(command.split())


main()

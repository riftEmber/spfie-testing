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
BIN_OUTPUT_DIR = "bin"
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
    os.mkdir(BIN_OUTPUT_DIR)

    t_declarations = ""
    for i in range(10):
        t_declarations += f"int t{i};\n"
    t_declarations += "\n"

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

            # get original and optimized kernel snippets
            kernel_function_name = "kernel_" + kernel_name.replace('-', '_')
            print_debug(f"searching for function {kernel_function_name}")
            with open(f"{kernel_path}/{kernel_name}.preproc.c") as preprocessed:
                preprocessed_lines = preprocessed.readlines()

                # extract original kernel
                start_line = find_kernel_start(preprocessed_lines, kernel_function_name)
                end_line = find_next_instance_line(preprocessed_lines, start_line, "}")
                kernel_snippet_lines = [x for x in preprocessed_lines[start_line:end_line] if "pragma" not in x]
                kernel_snippet = "".join(kernel_snippet_lines)
                print_debug("original:\n" + kernel_snippet)

                with open(TMP_KERNEL_FILE, "w") as tmp_file:
                    tmp_file.write(kernel_snippet)
                spfie_run_output = subprocess.run(
                    f"../../build/bin/spf-ie {TMP_KERNEL_FILE} --entry-point {kernel_function_name}".split(),
                    capture_output=True)
                if spfie_run_output.returncode != 0:
                    print(f"spf-ie run on kernel '{kernel_name}' had exit code of {spfie_run_output.returncode}")
                    print("spf-ie stderr:")
                    print(spfie_run_output.stderr.decode())
                    print(f"skipping kernel {kernel_name}")
                    failure_count += 1
                    # sys.exit()
                    continue
                optimized_snippet = t_declarations + spfie_run_output.stdout.decode()
                print_debug("optimized:\n" + optimized_snippet)
            # generate kernel files with original and optimized snippets
            with open(f"{kernel_path}/{kernel_name}.c") as source_kernel_file:
                # get source code on either side of kernel body
                source_kernel_lines = source_kernel_file.readlines()
                declaration_start_line = find_kernel_start(source_kernel_lines, kernel_function_name)
                body_start_line = find_next_instance_line(source_kernel_lines, declaration_start_line, "{")
                body_end_line = find_next_instance_line(source_kernel_lines, body_start_line, "}")
                preamble = "".join(source_kernel_lines[:body_start_line])
                postamble = "".join(source_kernel_lines[body_end_line:])

                # remove signature from kernel snippet
                body_start_line = find_next_instance_line(kernel_snippet_lines, 0, "{")
                kernel_snippet_no_signature = "".join(kernel_snippet_lines[body_start_line:])

                # create unoptimized and optimized source files
                print_debug("writing original and optimized source files")
                with open(f"{PROCESSED_SRC_DIR}/{kernel_name}.orig.c", "w+") as original_file:
                    original_file.write(preamble + kernel_snippet_no_signature + postamble)
                with open(f"{PROCESSED_SRC_DIR}/{kernel_name}.opt.c", "w") as optimized_file:
                    optimized_file.write(preamble + optimized_snippet + "}" + postamble)

                # compile files
                print_debug("compiling executables")
                optimized_binary = f"{BIN_OUTPUT_DIR}/{kernel_name}_opt"
                original_binary = f"{BIN_OUTPUT_DIR}/{kernel_name}_orig"
                run_cmd(
                    f"gcc -I utilities -I {kernel_path} utilities/polybench.c {PROCESSED_SRC_DIR}/{kernel_name}.orig.c -o {original_binary}")
                run_cmd(
                    f"gcc -I utilities -I {kernel_path} utilities/polybench.c {PROCESSED_SRC_DIR}/{kernel_name}.opt.c -o {optimized_binary}")

                # execute binaries
                print(f"Timing default {kernel_name} kernel...")
                run_cmd(f"time {original_binary}")
                print(f"Timing spf-ie'd {kernel_name} kernel...")
                run_cmd(f"time {optimized_binary}")
        print(
            f"{num_benchmarks} benchmarks processed, {num_benchmarks - failure_count} succeeded, {failure_count} failed")


def run_cmd(command):
    cmd_result = subprocess.run(command.split(),
                                capture_output=True)
    if cmd_result.returncode != 0:
        print("Failed cmd stderr: " + cmd_result.stderr.decode())
        cmd_result.check_returncode()


def print_debug(msg):
    if DEBUG:
        print("debug: " + msg)


def find_kernel_start(lines, name):
    line_number = 0
    for line in lines:
        if name in line:
            break
        else:
            line_number += 1
    if line_number >= len(lines):
        sys.exit(f"Could not find kernel function '{name}'!")
    else:
        return line_number - 1


def find_next_instance_line(lines, start_line, target):
    line_number = start_line
    for line in lines[start_line:]:
        if line.rstrip() == target:
            break
        else:
            line_number += 1
    if line_number >= len(lines):
        sys.exit(f"Could not find next instance of {target} in current kernel!")
    else:
        return line_number + 1


main()

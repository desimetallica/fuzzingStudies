#!/usr/bin/python3

from fuzzingbook import bookutils
import random
import os
import tempfile
import subprocess

def fuzzer(max_length: int = 100, char_start: int = 32, char_range: int = 32) -> str:
    """A string of up to `max_length` characters
       in the range [`char_start`, `char_start` + `char_range`)"""
    string_length = random.randrange(0, max_length + 1)
    out = ""
    for i in range(0, string_length):
        out += chr(random.randrange(char_start, char_start + char_range))
    return out

print(fuzzer())
print("\n")
print(fuzzer(1000, ord('a'), 26))
print("\n")
print(fuzzer(100, ord('0'), 10))

basename = "input.txt"
tempdir = tempfile.mkdtemp()

FILE = os.path.join(tempdir, basename)
print(FILE)

data = fuzzer()

with open(FILE, "w") as f:
    f.write(data)

contents = open(FILE).read()
print(contents)
assert(contents == data)

program = "bc"

with open(FILE, "w") as f:
    f.write("2 + 2\n")
result = subprocess.run([program, FILE],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True)

print("First bc run stdout: ", result.stdout)
print("First bc run returncode: ", result.returncode)
print("First bc run stderr: ", result.stderr)

trials = 100
program = "bc"

runs = []

for i in range(trials):
    data = fuzzer()
    with open(FILE, "w") as f:
        f.write(data)
    result = subprocess.run([program, FILE],
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)
    runs.append((data, result))

print("number of result with empty stderr: ")
print(sum(1 for (data, result) in runs if result.stderr == ""))

errors = [(data, result) for (data, result) in runs if result.stderr != ""]
(first_data, first_result) = errors[0]

print("number of result with error: ", len(errors))
print(repr(first_data))
print(first_result.stderr)

print("Print strange result from error Array:  ", [result.stderr for (data, result) in runs if
 result.stderr != ""
 and "illegal character" not in result.stderr
 and "parse error" not in result.stderr
 and "syntax error" not in result.stderr])

print("Cause number of crashing with nonzero code are: ", sum(1 for (data, result) in runs if result.returncode != 0))


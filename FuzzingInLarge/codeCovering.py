#!/usr/bin/python3

import subprocess
import sys
import os
from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashInfo import CrashInfo
from Collector.Collector import Collector
import random
import tempfile

random.seed(0)
cmd = ["simply-buggy/maze"]

constants = [3735928559, 1111638594]

TRIALS = 1000

for itnum in range(0, TRIALS):
    current_cmd = []
    current_cmd.extend(cmd)

    for _ in range(0, 4):
        if random.randint(0, 9) < 3:
            current_cmd.append(str(constants[
                random.randint(0, len(constants) - 1)]))
        else:
            current_cmd.append(str(random.randint(-2147483647, 2147483647)))

    result = subprocess.run(current_cmd, stderr=subprocess.PIPE)
    stderr = result.stderr.decode().splitlines()
    crashed = False

    if stderr and "secret" in stderr[0]:
        print(stderr[0])

    for line in stderr:
        if "ERROR: AddressSanitizer" in line:
            crashed = True
            break

    if crashed:
        print("Found the bug!")
        break

print("Done!")



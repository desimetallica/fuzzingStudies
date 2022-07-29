#!/usr/bin/python3

import subprocess
import sys
import os
from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashInfo import CrashInfo
from Collector.Collector import Collector
import random
import tempfile

cmd = ["simply-buggy/out-of-bounds"]

def isascii(s):
    return all([0 <= ord(c) <= 127 for c in s])

def escapelines(bytes):
    def ascii_chr(byte):
        if 0 <= byte <= 127:
            return chr(byte)
        return r"\x%02x" % byte

    def unicode_escape(line):
        ret = "".join(map(ascii_chr, line))
        assert isascii(ret)
        return ret

    return [unicode_escape(line) for line in bytes.splitlines()]

# Connect to crash server
collector = Collector()

random.seed(2048)

crash_count = 0
TRIALS = 20

for itnum in range(0, TRIALS):
    rand_len = random.randint(1, 1024)
    rand_data = bytes([random.randrange(0, 256) for i in range(rand_len)])

    (fd, current_file) = tempfile.mkstemp(prefix="fuzztest", text=True)
    os.write(fd, rand_data)
    os.close(fd)

    current_cmd = []
    current_cmd.extend(cmd)
    current_cmd.append(current_file)

    result = subprocess.run(current_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout = []   # escapelines(result.stdout)
    stderr = escapelines(result.stderr)
    crashed = False

    for line in stderr:
        if "ERROR: AddressSanitizer" in line:
            crashed = True
            break

    print(itnum, end=" ")

    if crashed:
        sys.stdout.write("(Crash) ")

        # This reads the simple-crash.fuzzmanagerconf file
        configuration = ProgramConfiguration.fromBinary(cmd[0])

        # This reads and parses our ASan trace into a more generic format,
        # returning us a generic "CrashInfo" object that we can inspect
        # and/or submit to the server.
        crashInfo = CrashInfo.fromRawCrashData(stdout, stderr, configuration)

        # Submit the crash
        collector.submit(crashInfo, testCase = current_file)

        crash_count += 1

    os.remove(current_file)

print("")
print("Done, submitted %d crashes after %d runs." % (crash_count, TRIALS))

#!/usr/bin/python3

import subprocess
import sys
from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashInfo import CrashInfo
from Collector.Collector import Collector

configuration = ProgramConfiguration.fromBinary('simply-buggy/simple-crash')
print(configuration.product, configuration.platform)

cmd = ["simply-buggy/simple-crash"]

result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
stderr = result.stderr.decode().splitlines()
#print(stderr[0:3])
stdout = result.stdout.decode().splitlines()

crashInfo = CrashInfo.fromRawCrashData(stdout, stderr, configuration)

collector = Collector()

collector.submit(crashInfo)



# SPDX-License-Identifier: MIT
# @author Syed Syed

import logging
import os

import cocotb_test.simulator

import cocotb
from cocotb.regression import TestFactory
from cocotb.triggers import Timer
from cosim_nvme import CosimNvme


class TB:
    def __init__(self, dut):
        self.dut = dut

        self.log = logging.getLogger("cocotb.tb")
        self.log.setLevel(logging.DEBUG)

        self.nvme = CosimNvme(dut, "localhost")

# process incoming tlps qemu cosim forever
@cocotb.test()
async def run_test_cosim(dut):
    tb = TB(dut);
    while True:
      await Timer(10, units="ns")

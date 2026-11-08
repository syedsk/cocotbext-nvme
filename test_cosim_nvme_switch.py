# SPDX-License-Identifier: MIT
# @author Syed Syed

import logging

import cocotb
from cocotb.triggers import Timer
from cosim_nvme_switch import CosimNvmeSwitch


class TB:
    def __init__(self, dut):
        self.dut = dut

        self.log = logging.getLogger("cocotb.tb")
        self.log.setLevel(logging.DEBUG)

        # NVMe endpoint(s) behind a cocotb switch; upstream -> QEMU cosim
        self.nvme_switch = CosimNvmeSwitch(dut, "localhost", num_endpoints=1)


# process incoming TLPs from QEMU cosim forever
@cocotb.test()
async def run_test_cosim_switch(dut):
    tb = TB(dut)
    while True:
        await Timer(10, unit="ns")

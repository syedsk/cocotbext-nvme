# SPDX-License-Identifier: MIT
# @author Syed Syed

from cocotb.triggers import Event, Timer, First
from cocotbext.pcie.core import Device
from cocotbext.nvme import NvmeEndpoint
from cocotbext.nvme.defs import *
import uuid

class CosimNvme():
    def __init__(self, dut, hostname, *args, **kwargs):
        self.dut = dut

        self.ep = NvmeEndpoint(dut)
        self.dev = Device(self.ep)

        #connect to the qemu cosim
        self.dev.start_cosim_server(hostname)


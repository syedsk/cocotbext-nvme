# SPDX-License-Identifier: MIT
# @author Syed Syed

import logging

from cocotbext.pcie.core.switch import Switch
from cocotbext.pcie.core.device import Device
from cocotbext.pcie.core.cosim_port import CosimPort
from cocotbext.nvme import NvmeEndpoint
from cocotbext.nvme import NvmeController
from cocotbext.nvme.defs import *


class CosimNvmeSwitch():
    """
    NVMe endpoint(s) behind a cocotb PCIe switch; switch upstream -> QEMU cosim.

        QEMU (cocotb-pcie-switch 'cps0')
          |  ZMQ
        CosimPort  <-- switch upstream link partner
          |
        Switch (SwitchUpstreamPort)
          +-- SwitchDownstreamPort.downstream SimPort
                 <==link==>
              Device.upstream SimPort --> NvmeEndpoint
    """
    def __init__(self, dut, hostname, num_endpoints=1, *args, **kwargs):
        self.dut = dut
        self.log = logging.getLogger("cocotb.pcie.CosimNvmeSwitch")
        self.log.setLevel(logging.DEBUG)

        # 1. Cosim transport facing QEMU (defaults match cps0 ports:
        #    port=5555, push_port=6001, pull_port=6000)
        self.cosim = CosimPort()

        # 2. Build the switch
        self.switch = Switch(upstream_port=self.cosim)

        # 3. For each endpoint: wrap in a Device (SimPort upstream),
        #    connect the Device's SimPort to a switch downstream port.
        self.devices = []
        self.endpoints = []
        for i in range(num_endpoints):
            ep = NvmeEndpoint()

            dev = Device(ep)
            # Create a switch downstream port and link the two SimPorts.
            dsp = self.switch.make_port()          # SwitchDownstreamPort
            dsp.connect(dev.upstream_port)         # DSP SimPort <-> Device SimPort

            self.devices.append(dev)
            self.endpoints.append(ep)
            self.log.info("DSP %d <-> Device -> NvmeEndpoint vid=%#06x",
                          i, ep.vendor_id)

        # 4. Bind ZMQ sockets (QEMU connects to these)
        self.cosim.start_cosim_server(hostname)

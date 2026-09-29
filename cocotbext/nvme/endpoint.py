# SPDX-License-Identifier: MIT
# @author Syed Syed

from cocotb.triggers import Event, Timer, First
from cocotbext.pcie.core.caps import MsixCapability
from cocotbext.pcie.core.caps import SriovExtendedCapability
from cocotbext.pcie.core import Device
from cocotbext.pcie.core.utils import PcieId
from cocotbext.pcie.core import MemoryEndpoint
from .controller import NvmeController
from .defs import *
import uuid

class VirtNvmeEndpoint(MemoryEndpoint):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        print("Creating VF Endpoint")
        self.vendor_id = 0xffff
        self.device_id = 0xffff

        self.pf = None
        self.is_pf = False
        self.ctrlr = None

        self.revision_id = 0x0
        # nvme 
        self.class_code = (0x1 << 16) | (0x8 << 8) | 0x2

        self.msi_cap = MsixCapability()
        self.msi_cap.msix_table_size = 8
        self.msi_cap.msix_enable = False
        self.msi_cap.msix_table_bar_indicator_register = 1
        self.msi_cap.msix_table_offset = 0x00000000
        self.msi_cap.msix_pba_bar_indicator_register = 1
        self.msi_cap.msix_pba_offset = 0x000000100
        self.register_capability(self.msi_cap)

        self.add_mem_region(8*1024)
        self.add_prefetchable_mem_region(4*1024)

        # init EF100 bar
        # initialize caps
        caps = nvme_caps()
        caps.mpsmax.integer = 4
        caps.mpsmin.integer = 0
        caps.cqr.integer = 0
        caps.dstrd.integer = 0
        caps.css.integer = 1
        caps.timeout.integer = 6
        caps.ams.integer = 1
        caps.mqes.integer = 0xfff #4k 
        print ("caps: ", hex(caps.to_bus(bigEndian=False).integer))
        self.init_mem_region(0, 0x0, caps.to_bus(bigEndian=False).buff) 
        version = nvme_version()
        version.mjr.integer = 0x1
        version.mnr.integer = 0x4
        version.ter.integer = 0x0
        self.init_mem_region(0, 0x8, version.to_bus(bigEndian=False).buff) 
        self.csts = nvme_csts()
        self.csts.ready.integer = 0
        self.init_mem_region(0, 0x1c, self.csts.to_bus(bigEndian=False).buff)

class NvmeEndpoint(MemoryEndpoint):
    def __init__(self, dut, *args, **kwargs):

        super().__init__(*args, **kwargs)
        print("Creating PF Endpoint")
        self.vendor_id = 0x10ee
        self.device_id = 0x0100

        self.is_pf = True
        self.virt_functions = []

        self.ctrlr = NvmeController(dut, self)
        self.revision_id = 0x0
        # nvme
        self.class_code = (0x1 << 16) | (0x8 << 8) | 0x2

        self.msi_cap = MsixCapability()
        self.msi_cap.msix_table_size = 31 #zero based value
        self.msi_cap.msix_enable = False
        self.msi_cap.msix_table_bar_indicator_register = 1
        self.msi_cap.msix_table_offset = 0x00000000
        self.msi_cap.msix_pba_bar_indicator_register = 1
        self.msi_cap.msix_pba_offset = 0x00001000
        self.register_capability(self.msi_cap)

        self.sriov_cap = SriovExtendedCapability()
        self.register_extended_capability(self.sriov_cap)

        self.add_mem_region(32*1024)
        self.add_mem_region(16*1024)


        # init EF100 bar
        # initialize caps
        caps = nvme_caps()
        caps.cmbs.integer = 0
        caps.mpsmax.integer = 4
        caps.mpsmin.integer = 0
        caps.cqr.integer = 0
        caps.dstrd.integer = 0
        caps.css.integer = 1
        caps.timeout.integer = 6
        caps.ams.integer = 1
        caps.mqes.integer = 0xfff #4k
        self.init_mem_region(0, 0x0, caps.to_bus(bigEndian=False).buff)
        version = nvme_version()
        version.mjr.integer = 0x1
        version.mnr.integer = 0x4
        version.ter.integer = 0x0
        self.init_mem_region(0, 0x8, version.to_bus(bigEndian=False).buff)
        csts = nvme_csts()
        csts.ready.integer = 0
        self.init_mem_region(0, 0x1c, csts.to_bus(bigEndian=False).buff)
        cmbsz = nvme_cmbsz()
        cmbsz.sz.integer = 0
        self.init_mem_region(0, 0x3c, cmbsz.to_bus(bigEndian=False).buff)

    async def create_vf(self, num_vf, pciId, fn):
        print("CREATING VF:",num_vf, "PCIID:",pciId)
        bdf = pciId.bus << 8 | pciId.device << 3 | fn;
        sriov_reg5 = await self.ext_capabilities.read_register(0x45)
        vf_offset = sriov_reg5 & 0x0000ffff
        vf_stride = (sriov_reg5 >> 16) & 0x0000ffff 
        bdf = bdf + vf_offset
        for i in range(num_vf):
            virt_func = VirtNvmeEndpoint()
            virt_func.ctrlr = nvmeCtrlr(virt_func) 
            virt_func.pcie_id = PcieId(bdf >> 8, (bdf >> 3) & 0x0000001f, bdf & 7)
            print("CREATED VF:",virt_func.pcie_id)
            virt_func.pf = self
            virt_func.vendor_id = 0xffff
            virt_func.device_id = 0x1010 #0xffff
            virt_func.class_code = (0x1 << 16) | (0x8 << 8) | 0x2
            virt_func.identify_ctrl.cntlid.integer = self.identify_ctrl.cntlid.integer + vf_offset + i * vf_stride
            bar0_start_add = self.sriov_cap.bar[0]
            bar1_start_add = self.sriov_cap.bar[1]
            bar2_start_add = self.sriov_cap.bar[2]
            virt_func.bar[0] = bar0_start_add + i*(8*1024)
            virt_func.bar[1] = bar1_start_add + i*(4*1024)

            virt_func.upstream_tx_handler = self.upstream_tx_handler
            self.virt_functions.append(virt_func)
            bdf = bdf + vf_stride


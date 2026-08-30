
from .common import PciExtCapId, PciExtCap
from cocotbext.pcie.core.utils import byte_mask_update

class SriovExtendedCapability(PciExtCap):
    """SR-IOV Extended Capability"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cap_id = PciExtCapId.SRIOV
        self.length = 16
        self.version = 1

        # SRIOV Capability Registers
        self.vf_enable = True
        self.vf_mse = True
        self.initial_vfs = 100
        self.total_vfs = 100
        self.num_vfs = 0xffff

        self.first_vf_offset = 1
        self.vf_stride = 1
        self.vf_dev_id = 0x0100

        self.sup_page_size = 0x553
        self.sys_page_size = 0x553

        self.bar = [0]*6
        self.bar_mask = [0]*6

        self.mig_state_arr = 0
    """
    SR-IOV Capability

    31                                                                  0
    +---------------------+-----------+---------------------------------+
    |         Next Cap    | Version   |             Cap ID              |   0   0x00
    +---------------------+-----------+---------------------------------+
    |                         SR-IOV Capabilities                       |   1   0x04
    +---------------------------------+---------------------------------+
    |        SR-IOV Status            |         SR-IOV Control          |   2   0x08
    +---------------------------------+---------------------------------+
    |        Total VFs                |         Initial VFs             |   3   0x0C
    +----------------+----------------+---------------------------------+
    |     RsvdP      |   FuncDepLink  |         Num VFs                 |   4   0x10
    +----------------+----------------+---------------------------------+
    |        VF Stride                |    First VF Offset              |   5   0x14
    +---------------------------------+---------------------------------+
    |        VF Device ID             |         RsvdP                   |   6   0x18
    +-------------------------------------------------------------------+
    |                     Supported Page Sizes                          |   7   0x1C
    +-------------------------------------------------------------------+
    |                     System Page Size                              |   8   0x20
    +-------------------------------------------------------------------+
    |                            VF BAR0                                |   9   0x24
    +-------------------------------------------------------------------+
    |                            VF BAR1                                |  10   0x28
    +-------------------------------------------------------------------+
    |                            VF BAR2                                |  11   0x2C
    +-------------------------------------------------------------------+
    |                            VF BAR3                                |  12   0x30
    +-------------------------------------------------------------------+
    |                            VF BAR4                                |  13   0x34
    +-------------------------------------------------------------------+
    |                            VF BAR5                                |  14   0x38
    +-------------------------------------------------------------------+
    |                   VF Migration State Array Offset                 |  15   0x3C
    +-------------------------------------------------------------------+
    """
    async def _read_register(self, reg):
        #print ("reading sriov register: ", reg)
        if reg == 0:
            # Version
            val = 0x10
            val |= (self.version & 0xf) << 16
            return val
        if reg == 1:
            # SR-IOV Capabilities
            val = 0
            return val
        if reg == 2:
            # Control
            val = bool(self.vf_enable)
            val |= bool(self.vf_mse) << 3
            return val
        if reg == 3:
            # VF Inital and total count
            val = self.initial_vfs
            val |= self.total_vfs << 16
            return val
        if reg == 4:
            # Number of VFs
            val = self.num_vfs
            return val
        if reg == 5:
            # VF stride and offset
            val = self.first_vf_offset
            val |= self.vf_stride << 16
            return val
        if reg == 6:
            # Device ID
            val = self.vf_dev_id << 16
            return val
        if reg == 7:
            # Page size supported
            val = self.sup_page_size
            return val
        if reg == 8:
            # System Page size
            val = self.sys_page_size
            return val
        if reg == 9:
            # Base Address Register 0
            return self.bar[0] & 0xffffffff
        if reg == 10:
            # Base Address Register 1
            return self.bar[1] & 0xffffffff
        if reg == 11:
            # Base Address Register 2
            return self.bar[2] & 0xffffffff
        if reg == 12:
            # Base Address Register 3
            return self.bar[3] & 0xffffffff
        if reg == 13:
            # Base Address Register 4
            return self.bar[4] & 0xffffffff
        if reg == 14:
            # Base Address Register 5
            return self.bar[5] & 0xffffffff
        if reg == 15:
            val = self.mig_state_arr
            return val

    async def _write_register(self, reg, val, mask):
        #print ("writing sriov register:", reg, "val:", val, "mask:", mask)
        if reg == 2:
            # Control
            if(mask & 0x3):
                self.vf_enable = True if (val & 1) else False
                self.vf_mse = True if (val & (1<<3)) else False
        if reg == 3:
            # Initial and total VFs count
            self.initial_vfs = val & 0x0000ffff
            self.total_vfs = val >> 16
        if reg == 4:
            # Number of VFs
            self.num_vfs = val
        if reg == 5:
            # VF stride and offset
            self.first_vf_offset = val & 0x0000ffff
            self.vf_stride = val >> 16
        if reg == 8:
            # System Page size
            self.sys_page_size = val 
        if reg == 9:
            # Base Address Register 0
            self.bar[0] = byte_mask_update(self.bar[0], mask, val, self.bar_mask[0])
        if reg == 10:
            # Base Address Register 1
            self.bar[1] = byte_mask_update(self.bar[1], mask, val, self.bar_mask[1])
        if reg == 11:
            # Base Address Register 2
            self.bar[2] = byte_mask_update(self.bar[2], mask, val, self.bar_mask[2])
        if reg == 12:
            # Base Address Register 3
            self.bar[3] = byte_mask_update(self.bar[3], mask, val, self.bar_mask[3])
        if reg == 13:
            # Base Address Register 4
            self.bar[4] = byte_mask_update(self.bar[4], mask, val, self.bar_mask[4])
        if reg == 14:
            # Base Address Register 5
            self.bar[5] = byte_mask_update(self.bar[5], mask, val, self.bar_mask[5])
        if reg == 15:
            # Migration array
            self.mig_state_arr = val

    def sriov_configure_bar(self, idx, size, ext=False, prefetch=False, io=False):
        mask = 2**((size-1).bit_length())-1
        if idx >= len(self.bar) or (ext and idx+1 >= len(self.bar)):
            raise Exception("BAR index out of range")

        if io:
            self.bar[idx] = 1
            self.bar_mask[idx] = 0xfffffffc & ~mask
        else:
            self.bar[idx] = 0
            self.bar_mask[idx] = 0xfffffff0 & ~mask

            if ext:
                self.bar[idx] |= 4
                self.bar[idx+1] = 0
                self.bar_mask[idx+1] = 0xffffffff & (~mask >> 32)

            if prefetch:
                self.bar[idx] |= 8
            
            
            

    

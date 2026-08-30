# cocotbext-nvme

NVMe endpoint model for [cocotb](https://www.cocotb.org/), built on top of
[cocotbext-pcie](https://github.com/alexforencich/cocotbext-pcie). It implements
a functional NVMe controller that can be driven by a real NVMe host driver
(e.g. the Linux kernel `nvme` driver) via QEMU cosimulation.

## Features

- NVMe controller model with Admin and I/O queue processing
- PCIe endpoint built by subclassing `cocotbext-pcie`'s `MemoryEndpoint`
- MSI-X interrupt generation
- Admin commands: Identify (Controller / Namespace / Active NS List),
  Create/Delete I/O SQ & CQ, Get Log Page, Set Features, Abort
- I/O commands: Read, Write (with PRP list / DMA handling)
- Configurable namespaces backed by sparse memory
- Connects to QEMU via a PCIe cosimulation transport

## Requirements

- Python 3.8+
- [cocotb](https://www.cocotb.org/)
- [cocotbext-pcie](https://github.com/alexforencich/cocotbext-pcie) (vendored under `cocotbext/pcie`)
- QEMU built with the `cocotb-pcie-endpoint` cosim device (https://github.com/syedsk/qemu)
- Linux host with the `nvme` driver and [`nvme-cli`](https://github.com/linux-nvme/nvme-cli) (for testing)
- 

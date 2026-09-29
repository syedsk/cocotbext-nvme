# cocotbext-nvme (RTL cosimulation branch)

NVMe endpoint model for [cocotb](https://www.cocotb.org/), built on top of
[cocotbext-pcie](https://github.com/alexforencich/cocotbext-pcie). It implements
a functional NVMe controller that can be driven by a real NVMe host driver
(e.g. the Linux kernel `nvme` driver) via QEMU cosimulation.

**This branch (`qemu_cosim_rtl`)** extends the model to cosimulate against an
**RTL DUT**: guest software drives the NVMe model, which in turn exercises real
RTL (a hardware gzip compressor) inside the cocotb simulator.

> **Note:** This is a *functional* cosimulation — it models protocol behavior and
> data correctness, not cycle-accurate timing or real-world performance.

## Features

- NVMe controller model with Admin and I/O queue processing
- PCIe endpoint built by subclassing `cocotbext-pcie`'s `MemoryEndpoint`
- MSI-X interrupt generation
- Admin commands: Identify (Controller / Namespace / Active NS List),
  Create/Delete I/O SQ & CQ, Get Log Page, Set Features, Abort
- I/O commands: Read, Write (with PRP list / DMA handling)
- Configurable namespaces backed by sparse memory
- Connects to QEMU via a PCIe cosimulation transport
- **RTL cosimulation:** drive a real hardware gzip compressor (RTL) from guest
  software through the NVMe data path

## Architecture

```
┌────────────────────────────────────────────────┐
│                     QEMU                         │
│    Linux guest ── nvme driver ── PCIe config     │
│                      │                           │
│          -device cocotb-pcie-endpoint            │
└──────────────────────┼───────────────────────────┘
                       │  cosim transport (TLPs)
┌──────────────────────┼───────────────────────────┐
│                cocotb + simulator                 │
│   ┌────────────────────────────────────────────┐ │
│   │ NvmeEndpoint (PCIe) ── NvmeController        │ │
│   │        │                                     │ │
│   │        └── data path ──► gzip RTL DUT        │ │
│   └────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

## Requirements

- Python 3.8+
- [cocotb](https://www.cocotb.org/)
- [cocotbext-pcie](https://github.com/alexforencich/cocotbext-pcie)
  (vendored under `cocotbext/pcie`)
- QEMU built with the `cocotb-pcie-endpoint` cosim device
  ([fork](https://github.com/syedsk/qemu))
- A supported HDL simulator (e.g. **Synopsys VCS**) for the RTL DUT
- Linux host with the `nvme` driver and
  [`nvme-cli`](https://github.com/linux-nvme/nvme-cli) (for testing)

## Getting the RTL (GPL — fetched as a submodule)

The RTL gzip compressor is the GPL-licensed
[FPGA-Gzip-compressor](https://github.com/WangXuan95/FPGA-Gzip-compressor) by
WangXuan95.

Clone with submodules, or initialize them after cloning:

```bash
# Clone including submodules
git clone --recurse-submodules -b qemu_cosim_rtl \
    git@github.com:syedsk/cocotbext-nvme.git

# Or, if already cloned:
git submodule update --init --recursive
```

The RTL sources are provided under `rtl/gzip/` after initialization.

<!-- CONFIRM: update the RTL path(s) below once repo structure is verified.
     find rtl/gzip -type f
     grep "^module" rtl/gzip/Arty-example/RTL/fpga_top.v
-->

## Usage

### 1. Build QEMU with `cocotb-pcie-endpoint`

```bash
../configure \
    --target-list=x86_64-softmmu \
    --enable-virtfs \
    --disable-gtk \
    --disable-sdl \
    --disable-gcrypt \
    --disable-curl \
    --disable-capstone \
    --disable-cap-ng \
    --enable-vnc \
    --enable-cap-ng \
    --disable-libusb \
    --disable-bzip2 \
    --enable-slirp

make -j$(nproc)
```

### 2. Run QEMU

```bash
#!/bin/bash
set -euo pipefail

TOP_DIR="$PWD"
X86_QEMU="$TOP_DIR/binaries/qemu-system-x86_64"
IMAGE="$TOP_DIR/binaries/jammy-server-cloudimg-amd64.img"
QEMU_BIOS_DIR="$TOP_DIR/binaries"

"$X86_QEMU" \
    -machine q35 \
    -L "$QEMU_BIOS_DIR" \
    -m 4096 \
    -smp 4 \
    -drive file="$IMAGE",format=qcow2 \
    -device pcie-root-port,id=rp0,bus=pcie.0,chassis=1,slot=0 \
    -device cocotb-pcie-endpoint,bus=rp0,addr=0x0 \
    -netdev user,id=eth0,hostfwd=tcp::2222-:22 \
    -net nic,netdev=eth0 \
    -serial mon:stdio \
    -vga none \
    -nographic
```

### 3. Run the RTL cosimulation

```bash
# Initialize the RTL submodule first (if not already done)
git submodule update --init --recursive

cd cocotbext-nvme
make
```

## Sample Output

In the QEMU guest:

```
ubuntu@ubuntu:~$ sudo nvme list
Node          SN                   Model                       Namespace  Usage                    Format          FW Rev
------------  -------------------  --------------------------  ---------  -----------------------  --------------  ------
/dev/nvme0n1  COSIM00000000000001  cocotbext-nvme controller   1          536.87 MB / 536.87 MB    512   B + 0 B   1.0
```

## Verifying the Device (in the guest)

```bash
sudo nvme list
sudo nvme id-ctrl /dev/nvme0
sudo nvme id-ns /dev/nvme0n1
sudo nvme smart-log /dev/nvme0
cat /proc/partitions
```

## Branches

- **`qemu_cosim`** — NVMe endpoint model cosimulated with QEMU (no RTL DUT)
- **`qemu_cosim_rtl`** — this branch; adds RTL DUT cosimulation (gzip compressor)

## Licensing

This project (`cocotbext-nvme`) is licensed under the **MIT License**.

It uses third-party components with their own licenses:

| Component | Author | License | Inclusion |
|-----------|--------|---------|-----------|
| cocotbext-pcie | Alex Forencich | MIT | Vendored under `cocotbext/pcie/` (notices retained) |
| [FPGA-Gzip-compressor](https://github.com/WangXuan95/FPGA-Gzip-compressor) | WangXuan95 | **GPL** |  referenced as a git submodule under `rtl/gzip/` |


## Acknowledgements

- [Alex Forencich](https://github.com/alexforencich) for `cocotbext-pcie`
- [WangXuan95](https://github.com/WangXuan95) for the FPGA gzip compressor RTL
- The [cocotb](https://www.cocotb.org/) project

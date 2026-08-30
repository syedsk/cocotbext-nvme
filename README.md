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
- [cocotbext-pcie](https://github.com/alexforencich/cocotbext-pcie)
  (vendored under `cocotbext/pcie`)
- QEMU built with the `cocotb-pcie-endpoint` cosim device
  ([fork](https://github.com/syedsk/qemu))
- Linux host with the `nvme` driver and
  [`nvme-cli`](https://github.com/linux-nvme/nvme-cli) (for testing)

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

### 3. Run the VCS cosimulation

```bash
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
# List NVMe devices
sudo nvme list

# Identify Controller (serial, model, firmware, capabilities)
sudo nvme id-ctrl /dev/nvme0

# Identify Namespace (size, capacity, LBA format)
sudo nvme id-ns /dev/nvme0n1

# SMART / health log
sudo nvme smart-log /dev/nvme0

# Kernel view of the block device
cat /proc/partitions
```

## Measuring IOPS (without fio)

Since the device is cosimulated, expect low IOPS — the goal is functional
correctness, not throughput.

```bash
# Live IOPS while running a workload (r/s + w/s)
iostat -x 1 /dev/nvme0n1

# Simple read workload
sudo dd if=/dev/nvme0n1 of=/dev/null bs=4k count=10000 iflag=direct

# Latency + IOPS
sudo ioping -D -s 4k -c 100 /dev/nvme0n1
```

## License

MIT License. This project builds on and vendors
[cocotbext-pcie](https://github.com/alexforencich/cocotbext-pcie)
(Copyright © Alex Forencich, MIT), whose copyright notice is retained in the
vendored files.

## Acknowledgements

- [Alex Forencich](https://github.com/alexforencich) for `cocotbext-pcie`
- The [cocotb](https://www.cocotb.org/) project

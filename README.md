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
- For co-simulation with real RTL (hardware gzip compressor) see [qemu_cosim_rtl](https://github.com/syedsk/cocotbext-nvme/tree/qemu_cosim_rtl) branch

## Architecture

```
┌────────────────────── QEMU ───────────────────────┐
│  Linux guest ── nvme driver ── PCIe config/MMIO/DMA │
│                        │                            │
│              -device cocotb-pcie-endpoint           │
└────────────────────────┼────────────────────────────┘
                         │  cosim transport(zmq sockets) (TLPs) 
┌────────────────────────▼────────────────────────────┐
│                  cocotb (Python)                     │
│   CosimNvme                                          │
│     └── NvmeEndpoint (PCIe MemoryEndpoint)           │
│           └── NvmeController                         │
│                 ├── Admin / I/O queue processing     │
│                 ├── Identify, Get Log, Set Features  │
│                 ├── MSI-X interrupts                 │
│                 └── Namespaces (sparse memory)       │
└──────────────────────────────────────────────────────┘
```

## Requirements

- Python 3.9+
- [cocotb](https://www.cocotb.org/) 2.x
- [cocotbext-pcie](https://github.com/alexforencich/cocotbext-pcie)
  (vendored under `cocotbext/pcie`)
- Python packages from `requirements.txt` (cocotb, cocotbext-axi,
  cocotb-test, pyzmq):
- QEMU built with the `cocotb-pcie-endpoint` cosim device
  ([fork](https://github.com/syedsk/qemu))
- Linux host with the `nvme` driver and
  [`nvme-cli`](https://github.com/linux-nvme/nvme-cli) (for testing)
- vcs or iverilog
- qemu [VM image](https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img)

## Usage

### 1. Build QEMU with `cocotb-pcie-endpoint`

```bash
../configure \
    --target-list=x86_64-softmmu \
    --extra-cflags=-Wno-error=discarded-qualifiers \
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
    --enable-slirp \
    --disable-docs

make -j$(nproc)
```

### 2. Run QEMU

```bash
#!/bin/bash
set -euo pipefail

TOP_DIR="$PWD"
X86_QEMU="$TOP_DIR/binaries/qemu-system-x86_64"
BASE_IMAGE="$TOP_DIR/binaries/jammy-server-cloudimg-amd64.img"
OVERLAY="$TOP_DIR/jammy-overlay.qcow2"
SEED="$TOP_DIR/seed.img"
QEMU_BIOS_DIR="$TOP_DIR/binaries"

# Keep the pristine cloud image untouched; write changes to an overlay
[ -f "$OVERLAY" ] || qemu-img create -f qcow2 -F qcow2 -b "$BASE_IMAGE" "$OVERLAY" 20G

# One-time cloud-init seed (sets password + SSH key for user 'ubuntu')
if [ ! -f "$SEED" ]; then
    cat > user-data <<'EOF'
#cloud-config
password: ubuntu
chpasswd: { expire: false }
ssh_pwauth: true
EOF
    echo "instance-id: jammy-cocotb" > meta-data
    cloud-localds "$SEED" user-data meta-data
fi


EP_OPTS="cocotb-pcie-endpoint,bus=rp0,addr=0x0"
EP_OPTS+=",np_port=5555,push_port=6000,pull_port=6001"
EP_OPTS+=",bar0_size=16384,bar0_type=0,bar1_size=16384,bar1_type=0"

"$X86_QEMU" \
    -machine q35 \
    -L "$QEMU_BIOS_DIR" \
    -m 4096 \
    -smp 4 \
    -drive file="$OVERLAY",format=qcow2 \
    -drive file="$SEED",format=raw \
    -device pcie-root-port,id=rp0,bus=pcie.0,chassis=1,slot=0 \
    -device "$EP_OPTS" \
    -netdev user,id=eth0,hostfwd=tcp::2222-:22 \
    -net nic,netdev=eth0 \
    -serial mon:stdio \
    -vga none \
    -nographic
```

### 3. Run the VCS/iverilog cosimulation

```bash
cd cocotbext-nvme
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
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
## Limitations
This cosimulation is functional, not timing-accurate: it faithfully models transactions and data, but not cycle-level timing or real hardware performance.
## License

MIT License. This project builds on and vendors
[cocotbext-pcie](https://github.com/alexforencich/cocotbext-pcie)
(Copyright © Alex Forencich, MIT), whose copyright notice is retained in the
vendored files.

## Acknowledgements

- [Alex Forencich](https://github.com/alexforencich) for `cocotbext-pcie`
- The [cocotb](https://www.cocotb.org/) project

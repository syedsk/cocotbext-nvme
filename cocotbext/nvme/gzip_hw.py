import logging
from cocotb.triggers import RisingEdge
from cocotbext.axi import (
    AxiStreamBus, AxiStreamSource, AxiStreamSink, AxiStreamFrame
)
from cocotb.clock import Clock
import cocotb


class GzipHwCompressor:
    """Wraps the RTL gzip compressor as a byte-in / byte-out engine."""

    def __init__(self, dut):
        self.dut = dut
        self.log = logging.getLogger("cocotb.gzip")

        # input side: 1-byte AXI-stream slave in RTL => source drives it
        self.source = AxiStreamSource(
            AxiStreamBus.from_prefix(dut, "i"),  # signals i_tvalid/i_tready/i_tdata/i_tlast
            dut.clk, dut.rstn, reset_active_level=False
        )

        # output side: 4-byte AXI-stream master in RTL => sink receives it
        self.sink = AxiStreamSink(
            AxiStreamBus.from_prefix(dut, "o"),  # o_tvalid/o_tready/o_tdata/o_tkeep/o_tlast
            dut.clk, dut.rstn, reset_active_level=False
        )
        dut.o_tready.value = 1  # keep receiver ready

    async def reset(self):
        self.dut.rstn.value = 0
        for _ in range(10):
            await RisingEdge(self.dut.clk)
        self.dut.rstn.value = 1
        for _ in range(10):
            await RisingEdge(self.dut.clk)

    async def compress(self, data: bytes) -> bytes:
        """Push raw bytes in, collect gzip stream out."""
        recv_task = cocotb.start_soon(self.sink.recv())
        # send input as one frame with tlast at the end
        frame = AxiStreamFrame(tdata=list(data))
        await self.source.send(frame)
        await self.source.wait()   # wait until fully accepted

        # receive compressed frame (tkeep handles the tail bytes < 4)
        out_frame = await recv_task

        # cocotbext-axi already applies tkeep to produce correct byte count
        compressed = bytes(out_frame.tdata)
        self.log.info("compress: in=%d bytes -> out=%d bytes",
                      len(data), len(compressed))
        return compressed


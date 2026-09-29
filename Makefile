# Copyright (c) 2020 Alex Forencich
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

TOPLEVEL_LANG = verilog

SIM ?= vcs
WAVES ?= 0

COCOTB_HDL_TIMEUNIT = 1ns
COCOTB_HDL_TIMEPRECISION = 1ps

DUT      = test_cosim_nvme
TOPLEVEL = $(DUT)
MODULE   = $(DUT)
export VERILOG_INCLUDE_DIRS = $(shell pwd)
VERILOG_SOURCES += $(shell pwd)/$(DUT).sv 
VERILOG_SOURCES += $(shell pwd)/rtl/calc_length_and_crc32.v
VERILOG_SOURCES += $(shell pwd)/rtl/convert_lz77_to_symbols.v
VERILOG_SOURCES += $(shell pwd)/rtl/dist_huffman_builder.v
VERILOG_SOURCES += $(shell pwd)/rtl/elastic_fifo_for_output.v
VERILOG_SOURCES += $(shell pwd)/rtl/fifo2_for_input.v
VERILOG_SOURCES += $(shell pwd)/rtl/gzip_compressor_top.v
VERILOG_SOURCES += $(shell pwd)/rtl/huffman_compress.v
VERILOG_SOURCES += $(shell pwd)/rtl/lz77_encoder.v
VERILOG_SOURCES += $(shell pwd)/rtl/lz77_hash_table_ram.v
VERILOG_SOURCES += $(shell pwd)/rtl/lz77_past_byte_ram.v
VERILOG_SOURCES += $(shell pwd)/rtl/split_stream_to_block.v
VERILOG_SOURCES += $(shell pwd)/rtl/static_huffman_table.v
VERILOG_SOURCES += $(shell pwd)/rtl/symbol_huffman_builder.v


include $(shell cocotb-config --makefiles)/Makefile.sim


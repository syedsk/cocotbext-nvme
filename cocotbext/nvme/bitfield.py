# SPDX-License-Identifier: MIT
# @author Syed Syed

import cocotb 
from cocotb.binary import BinaryValue

class bitfield():
    def __init__(self, *args, **kwargs):
        pass
    def to_bus(self, bigEndian=True):
        attributes = vars(self)

        valr = ''
        for value in attributes.values():
            valr += value.binstr

        vec = BinaryValue(valr, bigEndian=bigEndian)
        return vec

    def bus_len(self):
        attributes = vars(self)
        buslen = 0
        for value in attributes.values():
            buslen += value.n_bits
        return buslen

    # convert from bytes to fields
    def populate(self, vec):
        attributes = vars(self)

        if vec.big_endian is True:
            ofs = 0
            for value in attributes.values():
                atr_len = value.n_bits
                value.integer = vec[ofs:(ofs + atr_len - 1)]
                ofs += atr_len
        else:
            ofs = vec.n_bits - 1
            for value in attributes.values():
                atr_len = value.n_bits
                value.integer = vec[ofs:(ofs - atr_len + 1)]
                ofs -= atr_len

    def reset(self):
        attributes = vars(self)     

        for value in attributes.values():
            value.integer = 0

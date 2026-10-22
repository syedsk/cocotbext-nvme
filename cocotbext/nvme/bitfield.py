# SPDX-License-Identifier: MIT
# @author Syed Syed

import cocotb 

class BitVector:
    """Fixed-width mutable bit vector."""
    __slots__ = ("_nbits", "_v", "byteorder")

    def __init__(self, value=0, n_bits=0, byteorder="little"):
        self._nbits = n_bits
        self.byteorder = byteorder
        self._v = int(value) & ((1 << n_bits) - 1) if n_bits else int(value)

    # ---- width ------------------------------------------------------
    @property
    def n_bits(self):
        return self._nbits

    def __len__(self):
        return self._nbits

    # ---- integer value (get/set) -----------------------------------
    @property
    def integer(self):
        return self._v

    @integer.setter
    def integer(self, v):
        self._v = int(v) & ((1 << self._nbits) - 1)

    @property
    def signed_integer(self):
        v = self._v
        if self._nbits and (v >> (self._nbits - 1)):
            v -= (1 << self._nbits)
        return v

    # ---- bit string -------------------------------------------------
    @property
    def binstr(self):
        return format(self._v, f"0{self._nbits}b")

    def __str__(self):
        return self.binstr

    # ---- bytes (get/set) -------------------------------------------
    @property
    def buff(self):
        return self._v.to_bytes((self._nbits + 7) // 8, self.byteorder)

    @buff.setter
    def buff(self, b):
        self._v = int.from_bytes(bytes(b), self.byteorder) & ((1 << self._nbits) - 1)

    # ---- assign from raw bytes / vector ----------------------------
    def assign(self, data):
        if isinstance(data, (bytes, bytearray)):
            self._v = int.from_bytes(bytes(data), self.byteorder) & ((1 << self._nbits) - 1)
        elif isinstance(data, BitVector):
            self._v = data._v & ((1 << self._nbits) - 1)
        else:
            self.integer = int(data)

    def __int__(self):
        return self._v

    def __index__(self):
        return self._v

    def __repr__(self):
        return f"BitVector(n_bits={self._nbits}, 0x{self._v:x})"

def binval(nb):
    return BitVector(0, nb)

class bitfield:
    def __init__(self, *args, **kwargs):
        pass

    def _fields(self):
        return vars(self)

    def bus_len(self):
        return sum(f.n_bits for f in self._fields().values())

    def to_int(self):
        acc = 0
        shift = 0
        for f in reversed(list(self._fields().values())):
            acc |= (f.integer & ((1 << f.n_bits) - 1)) << shift
            shift += f.n_bits
        return acc

    def to_bytes(self, byteorder="little"):
        nbytes = (self.bus_len() + 7) // 8
        return self.to_int().to_bytes(nbytes, byteorder)

    def populate(self, data, byteorder="little"):
        if isinstance(data, (bytes, bytearray)):
            acc = int.from_bytes(bytes(data), byteorder)
        elif isinstance(data, BitVector):
            acc = data.integer
        else:
            acc = int(data)
        for f in reversed(list(self._fields().values())):
            f.integer = acc & ((1 << f.n_bits) - 1)
            acc >>= f.n_bits

    def reset(self):
        for f in self._fields().values():
            f.integer = 0


__all__ = ["bitfield", "BitVector", "binval"]

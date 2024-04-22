"""
All "complex" data types that are not covered in simple

Include modifications from https://github.com/ammaraskar/pyCraft/blob/master/minecraft/networking/types/basic.py
"""

import pynbt
from io import BytesIO

try:
    from simple import *
    from type import Type
except ImportError:
    from .simple import *
    from .type import Type

__all__ = ["VarInt", "VarLong", "Position", "Angle", "String", "FixedPoint", "FixedPointInt", "NBT"]

class LogicalShiftNum:
    def __init__(self, sign, mag, bits=32):
        self.sign = sign
        self.mag = mag
        self.bits = bits

    @classmethod
    def from_bits(cls, num, bits=32):
        if num >= 2 ** (bits - 1):
            mask = 2 ** (bits - 1) - 1
            num &= mask
            num = 2 ** (bits - 1) - num
            return cls(-1, num, bits)
        elif num < 0:
            m = 2 ** bits
            num = m - num
            return cls(-1, num, bits)
        else:
            return cls(1, num, bits)

    def twos_complement(self) -> int:
        if self.sign == -1:
            t = 2 ** (self.bits + 1)
            d = t - self.mag
            d &= ~(t >> 1)
            return d
        else:
            return self.mag

    def __rshift__(self, digits):
        """
        Logical right shift
        """
        return self.from_bits(self.twos_complement() >> digits, self.bits)

class VarInt(Type):
    SEGMENT_BITS = 0x7F
    CONTINUE_BIT = 0x80
    MAX_POSITION = 5
    BITS = 32

    def __init__(self, value: int):
        super().__init__(value)

    def serialize(self) -> bytes:
        value = bytes()
        v = LogicalShiftNum.from_bits(self.value, self.BITS)
        while True:
            if v.twos_complement() & ~self.SEGMENT_BITS == 0:
                value += v.twos_complement().to_bytes()
                break

            value += ((v.twos_complement() & self.SEGMENT_BITS) | self.CONTINUE_BIT).to_bytes()
            v >>= 7

        return value

    @classmethod
    def deserialize(cls, value: BytesIO):
        val = LogicalShiftNum(1, 0, cls.BITS)
        position = 0

        while True:
            current = int.from_bytes(value.read(1))
            val = LogicalShiftNum.from_bits(val.twos_complement() | (current & cls.SEGMENT_BITS) << 7 * position, cls.BITS)
            if not current & cls.CONTINUE_BIT:
                break

            position += 1
            if position > cls.MAX_POSITION:
                raise RuntimeError(
                    f"{cls.__name__} is too big"
                )

        return cls(val.sign * val.mag)

    @staticmethod
    def size(value: int):
        size = 1
        while True:
            max_val = 2 ** (7 * size)
            if value < max_val:
                return size
            size += 1

class VarLong(VarInt):
    MAX_POSITION = 10
    BITS = 64

class Position(Type):
    def __init__(self, x: int, y: int, z: int):
        super().__init__((x, y, z))

    def serialize(self) -> bytes:
        return (((self.value[0] & 0x3FFFFFF) << 38) | ((self.value[2] & 0x3FFFFFF) << 12) | (self.value[1] & 0xFFF)).to_bytes()

    @classmethod
    def deserialize(cls, value: BytesIO):
        val = Long.deserialize(value).value
        return cls(val >> 38, val << 52 >> 52, val << 26 >> 38)

class Angle(Type):
    def __init__(self, value: float):
        """
        The angle is in degrees
        """
        super().__init__(value)

    def serialize(self) -> bytes:
        return UByte(round(256 * ((self.value % 360) / 360))).serialize()

    @classmethod
    def deserialize(cls, value: BytesIO):
        return Angle(360 * UByte.deserialize(value).value / 256)

class String(Type):
    def __init__(self, value: str):
        super().__init__(value)

    def serialize(self) -> bytes:
        encoded = self.value.encode("utf-8")
        length = VarInt(len(encoded)).serialize()
        return length + encoded

class FixedPoint(Type):
    def __init__(self, int_type: type[Type], fractional_bits=5):
        """
        To set the value, do FixedPoint.set_value() OR manually set value
        """
        super().__init__(0)
        self.int_type = int_type
        self.denominator = 2 ** fractional_bits

    def set_value(self, value: int):
        self.value = value
        return self

    def serialize(self) -> bytes:
        return self.int_type(self.value * self.denominator).serialize()

    def deserialize(self, value: BytesIO):
        fp = FixedPoint(self.int_type, self.denominator)
        fp.value = self.int_type.deserialize(value) / self.denominator

FixedPointInt = FixedPoint(Int)

class NBT(Type):
    def __init__(self, nbt: pynbt.TAG_Compound):
        super().__init__(nbt)

    def serialize(self) -> bytes:
        buffer = BytesIO()
        pynbt.NBTFile(name=None, value=self.value.value).save(buffer)
        return buffer.getvalue()

    @classmethod
    def deserialize(cls, value: BytesIO):
        return cls(pynbt.NBTFile(value))

if __name__ == "__main__":
    def to_bytes(s):
        hex_strings = s.replace("0x", "").split()
        byte_string = bytes([int(hx, 16) for hx in hex_strings])

        return byte_string

    print(VarInt(-1).serialize())
    print(to_bytes("0xff 0xff 0xff 0xff 0x0f"))

    print(VarInt.deserialize(BytesIO(to_bytes("0x80 0x80 0x80 0x80 0x08"))).value)
    print(-2147483648)

    print(VarLong(-9223372036854775808).serialize())
    print(to_bytes("0x80 0x80 0x80 0x80 0x80 0x80 0x80 0x80 0x80 0x01"))

    print(VarLong.deserialize(BytesIO(to_bytes("0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0x01"))).value)
    print(-1)

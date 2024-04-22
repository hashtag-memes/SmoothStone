"""
All "simple" data types for packets
"""

import struct
from io import BytesIO

try:
    from type import Type
except ImportError:
    from .type import Type

class SimpleType(Type):
    FORMAT = ""

    def __init__(self, value):
        super().__init__(value)

    def serialize(self) -> bytes:
        return struct.pack(self.FORMAT, self.value)

    @classmethod
    def deserialize(cls, value: BytesIO):
        return cls(struct.unpack(cls.FORMAT, value.read(struct.calcsize(cls.FORMAT))))

class IntType(SimpleType):
    def __init__(self, value: int):
        super().__init__(value)

__all__ = ["Bool", "Byte", "UByte", "Short", "UShort", "Int", "Long", "Float", "Double"]

class Bool(SimpleType):
    FORMAT = "?"
    def __init__(self, value: bool):
        super().__init__(value)

class Byte(IntType):
    FORMAT = ">b"

class UByte(IntType):
    FORMAT = ">B"

class Short(IntType):
    FORMAT = ">h"

class UShort(IntType):
    FORMAT = ">H"

class Int(IntType):
    FORMAT = ">i"

class Long(IntType):
    FORMAT = ">q"

class ULong(IntType):
    FORMAT = ">Q"

class Float(SimpleType):
    FORMAT = ">f"
    def __init__(self, value: float):
        super().__init__(value)

class Double(SimpleType):
    FORMAT = ">d"
    def __init__(self, value: float):
        super().__init__(value)

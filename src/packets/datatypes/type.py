"""
All datatypes must inherit from this class
"""

from io import BytesIO

__all__ = ["Type"]

class Type:
    def __init__(self, value):
        self.value = value

    def serialize(self) -> bytes:
        return bytes(self.value)

    @classmethod
    def deserialize(cls, value: BytesIO):
        return cls(int(value.read(1)))

    def __getattr__(self, item):
        return getattr(self.value, item)

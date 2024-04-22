"""
A Minecraft profile
"""

from dataclasses import dataclass

__all__ = ["Profile"]

@dataclass
class Profile:
    UUID: str
    username: str
    access_token: str
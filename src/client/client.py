"""
A basic Minecraft client
"""

import socket

try:
    from ..log import logger
    from ..auth.profile import Profile
except ImportError:
    from src.log import logger
    from src.auth.profile import Profile

class Client:
    def __init__(self, profile: Profile):
        self.profile = profile
        self.socket: socket.socket = socket.socket()

    def connect(self, server: str, port=25565):
        self.socket.connect((server, port))
        self.socket.send()

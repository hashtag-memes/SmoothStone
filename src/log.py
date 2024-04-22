"""
Simple logging module
"""

import os
import pathlib

__all__ = ["logger", "Logger"]

class Logger:
    def __init__(self, name, print=False, write_file=True, directory: pathlib.Path =None):
        self.name = name
        self.print = print
        self.write_file = write_file
        if self.write_file:
            if not directory:
                directory = pathlib.Path(os.environ.get("LOGGING_DIRECTORY", os.path.join(os.getcwd(), "logs")))
            self.file_path = directory / f"{name}.txt"
            if not self.file_path.parent.exists():
                self.file_path.parent.mkdir()
            self.file = open(self.file_path, "w+")

    def info(self, message):
        msg = f"[INFO] {self.name}: {message}"
        if self.print:
            print("\u001B[93m" + msg + "\u001B[0m")
        if self.write_file:
            self.file.write(msg + "\n")

    def error(self, message):
        msg = f"[ERROR] {self.name}: {message}"
        if self.print:
            print("\u001B[91m"+ msg + "\u001B[0m")
        if self.write_file:
            self.file.write(msg + "\n")

    def __del__(self):
        self.file.close()

def logger(name="", write_to_stdout=False, write_to_file=True) -> Logger:
    return Logger(f"SmoothStone{'.' + name if name else ''}", write_to_stdout, write_to_file)

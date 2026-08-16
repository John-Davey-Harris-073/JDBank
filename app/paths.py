import os
import sys


def resource_dir() -> str:
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def templates_dir() -> str:
    return os.path.join(resource_dir(), "templates")


def static_dir() -> str:
    return os.path.join(resource_dir(), "static")
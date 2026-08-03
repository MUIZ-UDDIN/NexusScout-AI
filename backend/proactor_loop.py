import asyncio
import sys


def proactor_factory(use_subprocess: bool = False):
    if sys.platform == "win32":
        return asyncio.ProactorEventLoop()
    return asyncio.SelectorEventLoop()

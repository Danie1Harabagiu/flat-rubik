
import asyncio
import pygame  # Explicit import lets the web packager preload pygame-ce.
from flat_rubik.app import run_async

if __name__ == "__main__":
    asyncio.run(run_async())

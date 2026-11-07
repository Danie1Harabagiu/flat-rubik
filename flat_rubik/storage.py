"""Atomic desktop files and persistent browser-local storage."""
import sys


def read_text(path):
    if sys.platform == "emscripten":
        import platform
        try:
            value = platform.window.localStorage.getItem("flat-rubik:" + path.name)
            return str(value) if value is not None else None
        except Exception as error:
            raise OSError("Browser storage unavailable") from error
    return path.read_text(encoding="utf-8") if path.exists() else None


def write_text(path, value):
    if sys.platform == "emscripten":
        import platform
        try:
            platform.window.localStorage.setItem("flat-rubik:" + path.name, value)
        except Exception as error:
            raise OSError("Browser storage unavailable") from error
    else:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(value, encoding="utf-8")
        temporary.replace(path)

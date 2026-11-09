"""Validated UI preferences, independent of cube states and editor drafts."""
import json
import math
from pathlib import Path
import time

from flat_rubik.storage import read_text, write_text

DEFAULTS = {"fit_mode": "auto", "view_mode": "Ambele", "controls_visible": True,
            "paths": False, "paused": False, "fullscreen": False, "active_mode": "rubik",
            "window_size": [1080, 800], "yaw": -.55, "pitch": .45, "search_budget": 30,
            "rubik_duration": 1, "puzzle45_duration": 1, "face_buttons": None, "zoom_x": 1, "zoom_y": 1,
            "equal_pieces": True, "unwrapped_zoom_x": 1, "unwrapped_zoom_y": 1, "zoom_axis": "XY"}


def normalized(values):
    result = {**DEFAULTS, "window_size": DEFAULTS["window_size"][:]}
    if not isinstance(values, dict):
        return result
    for key, choices in (("fit_mode", ("auto", "proportional", "wide", "tall")),
                         ("zoom_axis", ("XY", "X", "Y")),
                         ("view_mode", ("Ambele", "Cerc", "Cub", "Desf\u0103\u0219urat", "Desf\u0103\u0219urat + Cub")),
                         ("active_mode", ("rubik", "45"))):
        if values.get(key) in choices:
            result[key] = values[key]
    if values.get("view_mode") == "Desfasurat":
        result["view_mode"] = "Desf\u0103\u0219urat"
    elif values.get("view_mode") == "Desfasurat + Cub":
        result["view_mode"] = "Desf\u0103\u0219urat + Cub"
    for key in ("controls_visible", "paths", "paused", "fullscreen", "equal_pieces"):
        if type(values.get(key)) is bool:
            result[key] = values[key]
    if type(values.get("face_buttons")) is bool:
        result["face_buttons"] = values["face_buttons"]
    for key, low, high in (("zoom_x", .4, 3), ("zoom_y", .4, 3),
                           ("unwrapped_zoom_x", .4, 3), ("unwrapped_zoom_y", .4, 3),
                           ("yaw", -1e6, 1e6), ("pitch", -1.5, 1.5), ("search_budget", 1, 3600),
                           ("rubik_duration", .2, 3), ("puzzle45_duration", .2, 3)):
        value = values.get(key)
        if type(value) in (int, float) and low <= value <= high and math.isfinite(value):
            result[key] = value
    size = values.get("window_size")
    if isinstance(size, (list, tuple)) and len(size) == 2 and all(type(v) is int for v in size):
        if 320 <= size[0] <= 16384 and 360 <= size[1] <= 16384:
            result["window_size"] = list(size)
    return result


class PreferencesStore:
    def __init__(self, path=None, clock=time.monotonic):
        self.path = Path(path) if path else None
        self.clock = clock
        self.last_write = -math.inf
        self.signature = None
        self.message = ""
        self.present_keys = set()
        self.values = normalized({})
        if self.path:
            try:
                saved = read_text(self.path)
                if saved is not None:
                    data = json.loads(saved)
                    if data["version"] != 1 or not isinstance(data["settings"], dict):
                        raise ValueError("Unknown preferences")
                    self.present_keys = set(data["settings"])
                    self.values = normalized(data["settings"])
                    self.signature = json.dumps(self.values, sort_keys=True, allow_nan=False)
            except (OSError, ValueError, KeyError, TypeError):
                self.message = "Setarile nu pot fi citite; folosesc valorile implicite."

    def save(self, values, force=False):
        self.values = normalized(values)
        if not self.path:
            return
        signature = json.dumps(self.values, sort_keys=True, allow_nan=False)
        if signature == self.signature or not force and self.clock() - self.last_write < .25:
            return
        try:
            write_text(self.path, json.dumps({"version": 1, "settings": self.values}, allow_nan=False))
            self.signature = signature
            self.last_write = self.clock()
            self.message = ""
        except OSError:
            self.message = "Nu s-au putut salva setarile."

"""Atomic autosave of the two independent games; physical states are validated."""
import json
import math
from pathlib import Path

from flat_rubik.state import facelets, cube_from_facelets

SESSION_PATH = Path(__file__).resolve().parent.parent / "puzzle_session.json"


class SessionStore:
    def __init__(self, path=SESSION_PATH):
        self.path = Path(path) if path else None
        self.signature = None
        self.message = ""

    def restore(self, classic, variant):
        if not self.path or not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data["version"] != 1:
                raise ValueError("Unknown session version")
            colors = {(tuple(s["position"]), tuple(s["normal"])): s["color"] for s in data["rubik"]}
            cube = cube_from_facelets(colors)
            duration = float(data.get("rubik_duration", 1))
            if not math.isfinite(duration) or not .2 <= duration <= 3:
                raise ValueError("Invalid duration")
            variant.import_state(data["puzzle45"])
            classic.set_cube(cube)
            classic.set_duration(duration)
            self.message = "Pozitiile salvate au fost restaurate."
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError):
            self.message = "Salvarea nu poate fi citita. Pornire normala."

    def save(self, classic, variant):
        if not self.path:
            return
        signature = classic.cube.snapshot(), variant.revision, classic.duration, variant.duration
        if signature == self.signature:
            return
        data = {"version": 1, "rubik_duration": classic.duration,
                "rubik": [{"position": p, "normal": n, "color": color}
                          for (p, n), color in facelets(classic.cube).items()],
                "puzzle45": variant.export_state()}
        temporary = self.path.with_suffix(".tmp")
        try:
            temporary.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False), encoding="utf-8")
            temporary.replace(self.path)
            self.signature = signature
            self.message = "Salvare automata activa."
        except OSError:
            self.message = "Nu s-a putut salva pozitia."

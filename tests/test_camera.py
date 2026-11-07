import json
import random
import unittest
from unittest.mock import patch

from flat_rubik.camera_colors import ORDER, scan_cube
from flat_rubik.camera_capture import CameraSession
from flat_rubik.cube import Cube, FACE_COLORS, scramble
from flat_rubik.solver import facelet_string
from flat_rubik.state import facelets


def grids(cube):
    standard = facelet_string(cube)
    return {f: [FACE_COLORS[c] for c in standard[i * 9:i * 9 + 9]]
            for i, f in enumerate("URFDLB")}


class CameraTests(unittest.TestCase):
    def test_scans_preserve_scrambled_orientations(self):
        for seed in range(30):
            cube = Cube()
            cube.apply(scramble(30, random.Random(seed)))
            self.assertEqual(facelets(scan_cube(grids(cube))), facelets(cube))

    def test_missing_faces_counts_and_flipped_edge_rejected(self):
        with self.assertRaises(ValueError):
            scan_cube({})
        bad = grids(Cube())
        bad["F"][0] = "alb"
        with self.assertRaises(ValueError):
            scan_cube(bad)
        bad = grids(Cube())
        bad["F"][1], bad["U"][7] = bad["U"][7], bad["F"][1]
        with self.assertRaises(ValueError):
            scan_cube(bad)

    def test_browser_bridge_validation_and_cancel(self):
        class Bridge:
            event = None
            finished = False
            error_text = ""
            def pollJson(self): return json.dumps(self.event)
            def error(self, text): self.error_text = text
            def finish(self): self.finished = True
        bridge = Bridge()
        session = CameraSession()
        session.bridge, session.active, session.target = bridge, True, "solver"
        bridge.event = {"type": "submit", "grids": {}}
        self.assertIsNone(session.poll())
        self.assertTrue(session.active)
        self.assertTrue(bridge.error_text)
        bridge.event = {"type": "submit", "grids": grids(Cube())}
        target, cube = session.poll()
        self.assertEqual(target, "solver")
        self.assertTrue(cube.solved)
        self.assertTrue(bridge.finished)
        self.assertFalse(session.active)

    def test_desktop_companion_only_accepts_local_token_origin(self):
        import urllib.request
        import urllib.error
        with patch("webbrowser.open") as launch:
            session = CameraSession()
            session.start("editor")
        try:
            url = launch.call_args.args[0]
            origin = url.split('/', 3)[:3]
            origin = '/'.join(origin)
            self.assertIn("camera.js", urllib.request.urlopen(url).read().decode())
            payload = json.dumps({"type": "submit", "grids": grids(Cube())}).encode()
            request = urllib.request.Request(url + "event", data=payload, headers={"Origin": origin, "Content-Type": "application/json"})
            urllib.request.urlopen(request).close()
            target, cube = session.poll()
            self.assertEqual(target, "editor")
            self.assertTrue(cube.solved)
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(urllib.request.Request(url + "event", data=payload))
        finally:
            session.close()

    def test_camera_controls_have_distinct_click_targets(self):
        from flat_rubik.ui import layout
        from flat_rubik.solve_panel import solve_layout
        for size in ((390, 844), (1080, 800), (640, 700), (320, 360)):
            for editing in (False, True):
                actions = layout(size, editing=editing)[4]
                camera = actions["camera"]
                for name, rect in actions.items():
                    if name != "camera":
                        self.assertFalse(camera.colliderect(rect), (size, editing, name))
            actions = solve_layout(size)[1]
            self.assertFalse(actions["camera"].colliderect(actions["search"]))
            self.assertFalse(actions["camera"].colliderect(actions["stop"]))

"""Browser camera bridge and desktop loopback companion (no camera dependency)."""
import json
import sys
from flat_rubik.camera_colors import scan_cube


class CameraSession:
    def __init__(self):
        self.active = False
        self.target = None
        self.bridge = self.server = None

    def start(self, target):
        self.close()
        self.target = target
        if sys.platform == "emscripten":
            import platform
            self.bridge = platform.window.flatRubikCamera
            self.bridge.open()
        else:
            self._desktop()
        self.active = True

    def _desktop(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path
        from queue import Queue
        import secrets
        import threading
        import webbrowser
        self.incoming, self.outgoing = Queue(), Queue()
        token = secrets.token_urlsafe(24)
        script = (Path(__file__).resolve().parent.parent / "web" / "camera-client.js").read_bytes()
        incoming, outgoing = self.incoming, self.outgoing

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                    self.send_error(403)
                    return
                if self.path == f"/{token}/camera.js":
                    body, mime = script, "text/javascript"
                elif self.path == f"/{token}/":
                    body = ('''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Flat Rubik Camera</title>
<script src="camera.js"></script><p id="done">Scanare Flat Rubik</p><script>
flatRubikCamera.open(); let pending=false;
const timer=setInterval(async()=>{if(pending)return;pending=true;try{
const event=JSON.parse(flatRubikCamera.pollJson());
const r=await fetch('event',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(event)});
const reply=await r.json();if(reply.error)flatRubikCamera.error(reply.error);
if(reply.finish){clearInterval(timer);flatRubikCamera.finish();document.getElementById('done').textContent='Scanarea s-a incheiat. Poti inchide fila.';}
}catch(e){clearInterval(timer);flatRubikCamera.finish();document.getElementById('done').textContent='Conexiunea cu aplicatia s-a inchis.';}finally{pending=false;}},200);
</script>''').encode()
                    mime = "text/html; charset=utf-8"
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                origin = f"http://127.0.0.1:{self.server.server_port}"
                if (self.path != f"/{token}/event" or self.headers.get("Host") != origin[7:]
                        or self.headers.get("Origin") != origin):
                    self.send_error(403)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 16384:
                        raise ValueError
                    event = json.loads(self.rfile.read(length))
                    if event is not None:
                        incoming.put(event)
                    reply = outgoing.get_nowait() if not outgoing.empty() else {}
                    body = json.dumps(reply).encode()
                except (ValueError, TypeError):
                    self.send_error(400)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        webbrowser.open(f"http://127.0.0.1:{self.server.server_port}/{token}/")

    def poll(self):
        if not self.active:
            return None
        if self.bridge is not None:
            event = json.loads(str(self.bridge.pollJson()))
        else:
            event = self.incoming.get_nowait() if not self.incoming.empty() else None
        if not isinstance(event, dict):
            return None
        if event.get("type") == "cancel":
            self.close()
        elif event.get("type") == "submit":
            try:
                cube = scan_cube(event.get("grids"))
            except ValueError as error:
                if self.bridge is not None:
                    self.bridge.error(str(error))
                else:
                    self.outgoing.put({"error": str(error)})
            else:
                target = self.target
                self.close()
                return target, cube
        return None

    def close(self):
        if self.bridge is not None:
            self.bridge.finish()
            self.bridge = None
        if self.server is not None:
            import threading
            server = self.server
            self.outgoing.put({"finish": True})
            # Allow the companion to receive the finish event before closing.
            def shutdown():
                server.shutdown()
                server.server_close()
            timer = threading.Timer(1, shutdown)
            timer.daemon = True
            timer.start()
            self.server = None
        self.active = False

    def draw(self, screen):
        if not self.active or self.bridge is not None:
            return
        import pygame
        from flat_rubik.renderer import text_surface
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((30, 10, 45, 220))
        screen.blit(shade, (0, 0))
        for offset, text in enumerate(("Camera este deschisa in browser.", "Scaneaza si confirma cele sase fete.", "Esc sau clic aici: renunta.")):
            label = text_surface(text, 20, (255, 255, 255))
            screen.blit(label, label.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + offset * 28)))

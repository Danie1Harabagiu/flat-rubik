"""Package only game source, never local saves or repository metadata."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def build():
    staging = ROOT / "build" / "mobile"
    staging.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "main.py", staging / "main.py")
    package = staging / "flat_rubik"
    package.mkdir(exist_ok=True)
    for source in (ROOT / "flat_rubik").glob("*.py"):
        shutil.copy2(source, package / source.name)
    subprocess.run([
        sys.executable, "-m", "pygbag", "--build", "--no_opt",
        "--ume_block", "0", "--can_close", "0", "--width", "390", "--height", "844",
        "--title", "Flat Rubik", "--app_name", "flat-rubik",
        "--template", str(ROOT / "web" / "mobile.tmpl"), str(staging),
    ], cwd=ROOT, check=True)
    output = staging / "build" / "web"
    (output / ".nojekyll").touch()
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    for name in ("index.html", "favicon.png", "mobile.apk", "mobile.tar.gz", ".nojekyll"):
        shutil.copy2(output / name, destination / name)
    assets = ("solver-client.js", "solver-worker.js", "cube-core.js", "cube-solve.js",
              "cubejs-LICENSE.txt", "cubejs-NOTICE.txt")
    version = hashlib.sha256(b"".join((ROOT / "web" / name).read_bytes() for name in assets)).hexdigest()[:16]
    for name in assets:
        shutil.copy2(ROOT / "web" / name, destination / name)
    index = destination / "index.html"
    index.write_text(index.read_text(encoding="utf-8").replace('src="solver-client.js"',
                     f'src="solver-client.js?v={version}"'), encoding="utf-8")
    print(f"Web output: {destination}")


if __name__ == "__main__":
    build()

"""Manual browser smoke check; requires Playwright and an installed Chrome."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    context = browser.new_context(**{**p.devices["iPhone 13"], "device_scale_factor": 1,
                                     "viewport": {"width": 390, "height": 844}})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded")
    key = "flat-rubik:puzzle_session.json"
    page.wait_for_function("key => localStorage.getItem(key) !== null", arg=key, timeout=120000)
    page.wait_for_function("() => document.querySelector('#infobox').style.display === 'none'", timeout=120000)
    page.wait_for_timeout(1200)
    print("READY", page.locator('#canvas').evaluate("c => [c.width,c.height,c.getBoundingClientRect().toJSON()]"), flush=True)
    def state():
        saved = page.evaluate("key => JSON.parse(localStorage.getItem(key))", key)
        saved["rubik"] = sorted(saved["rubik"], key=lambda s: (s["position"], s["normal"]))
        return saved

    initial = state()["rubik"]
    def wait_for_cube(expected=None):
        for _ in range(150):
            current = state()["rubik"]
            if (expected is None and current != initial) or (expected is not None and current == expected):
                return
            page.wait_for_timeout(100)
        page.screenshot(path="build/mobile-failure.png")
        print("BROWSER ERRORS", errors, flush=True)
        raise AssertionError("Timed out waiting for the completed rotation")

    page.touchscreen.tap(100, 596)  # Red, clockwise.
    wait_for_cube()
    changed = state()["rubik"]
    assert changed != initial, "Touch must rotate the cube"
    page.touchscreen.tap(44, 596)  # Red, inverse.
    wait_for_cube(initial)
    assert state()["rubik"] == initial, "A tap and its inverse must restore the cube"
    page.touchscreen.tap(100, 596)
    wait_for_cube(changed)
    assert state()["rubik"] == changed
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("() => document.querySelector('#infobox').style.display === 'none'", timeout=120000)
    page.wait_for_timeout(2000)
    assert state()["rubik"] == changed, "Browser reload must restore the game"
    page.touchscreen.tap(195, 818)  # Switch to Puzzle 45.
    page.wait_for_timeout(300)
    page.touchscreen.tap(100, 596)
    page.wait_for_function("key => JSON.parse(localStorage.getItem(key)).puzzle45.history.length > 0", arg=key, timeout=15000)
    assert len(state()["puzzle45"]["history"]) == 1, "Touch must also rotate Puzzle 45"
    # Resize to another portrait phone size; the canvas must follow the viewport.
    page.set_viewport_size({"width": 360, "height": 740})
    page.wait_for_timeout(1500)
    canvas_size = page.locator("#canvas").evaluate("c => [c.width,c.height]")
    print("RESIZE", canvas_size, page.evaluate("[innerWidth,innerHeight]"), flush=True)
    assert canvas_size == [360, 740]
    page.screenshot(path="build/mobile-browser.png")
    assert not errors, errors
    print("PASS: touch rotation, inverse, both modes, persistent reload, viewport resize; no JavaScript errors")
    browser.close()

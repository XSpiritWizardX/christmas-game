"""Start a guest room with an independent desktop and touch client for each mode."""

import json
import os
import re
from playwright.sync_api import sync_playwright

MODES = (
    "workshop",
    "raceway",
    "avalanche",
    "chaos",
    "candy_maze",
    "lake",
    "heist",
    "boss",
    "sleigh",
    "ornaments",
)


def smoke(driver, browser, mode):
    desktop = browser.new_context()
    mobile = browser.new_context(**driver.devices["Pixel 7"])
    host, peer = desktop.new_page(), mobile.new_page()
    errors, worlds = [], {}

    def observe(data):
        if isinstance(data, str) and data.startswith('42["world_state",'):
            payload = json.loads(data[2:])[1]
            worlds[payload["room"]["roundType"]] = payload["world"]

    try:
        for page in (host, peer):
            page.on("pageerror", lambda err: errors.append(str(err)))
            page.goto(
                os.getenv("SMOKE_URL", "http://127.0.0.1:10000"),
                wait_until="domcontentloaded",
            )
        peer.on("websocket", lambda ws: ws.on("framereceived", observe))
        # Attach the observer before establishing the guest's fresh socket.
        peer.reload(wait_until="domcontentloaded")
        host.get_by_placeholder("Santa").fill("Snow QA")
        host.get_by_role("button", name="Create room").click()
        hud = host.locator(".hud-sub")
        hud.wait_for()
        code = re.search(r"Room (\w+)", hud.inner_text())[1]
        host.get_by_role("button", name="Menu", exact=True).click()
        host.get_by_role("button", name="Invite friends").click()
        invite = host.get_by_label("Room invite link").input_value()
        assert host.locator(".room-invite svg").is_visible()
        peer.goto(invite)
        assert peer.get_by_placeholder("ABCD").input_value() == code
        host.get_by_role("button", name="Close menu").click()
        peer.get_by_placeholder("Santa").fill("Mobile QA")
        peer.get_by_role("button", name="Join room").tap()
        peer.locator(".hud-sub").wait_for()
        host.get_by_role("button", name="Menu", exact=True).click()
        host.get_by_label("Level", exact=True).select_option(mode)
        host.get_by_role("button", name="Yeti", exact=True).click()
        host.get_by_role("button", name="Add AI").click()
        host.get_by_role("button", name="Start game").click()
        host.get_by_role("button", name="Start round 1").click()
        peer.locator(".timer-chip").wait_for()
        for _ in range(100):
            if mode in worlds:
                break
            peer.wait_for_timeout(50)
        players = worlds[mode]["players"]
        assert len(players) == 3 and any(p["isBot"] for p in players), mode
        assert any(p["character"] == "yeti" for p in players), mode
        p1 = next(p for p in players if p["name"] == "Snow QA")
        host.keyboard.down("d")
        host.wait_for_timeout(250)
        host.keyboard.up("d")
        host.keyboard.press("Space")
        peer.locator(".action-button").tap()
        p2 = next(p for p in worlds[mode]["players"] if p["id"] == p1["id"])
        assert p1["x"] != p2["x"], mode
        stick = peer.get_by_label("Movement joystick").bounding_box()
        point = {
            "x": stick["x"] + stick["width"] / 2 + 22,
            "y": stick["y"] + stick["height"] / 2,
        }
        guest = next(p for p in worlds[mode]["players"] if p["name"] == "Mobile QA")
        touch = mobile.new_cdp_session(peer)
        touch.send(
            "Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point]}
        )
        peer.wait_for_timeout(300)
        touch.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        for _ in range(40):
            latest = next(p for p in worlds[mode]["players"] if p["id"] == guest["id"])
            if latest["x"] != guest["x"]:
                break
            peer.wait_for_timeout(50)
        assert latest["x"] != guest["x"], mode
        if mode == "boss":
            peer.reload(wait_until="domcontentloaded")
            peer.get_by_role("button", name="Strike", exact=True).wait_for()
            assert code in peer.locator(".hud-sub").inner_text()
            peer.get_by_role("button", name="Menu", exact=True).tap()
            peer.get_by_label("Action button side").select_option("left")
            peer.get_by_label("Control size").select_option("large")
            peer.reload(wait_until="domcontentloaded")
            peer.get_by_role("button", name="Strike", exact=True).wait_for()
            assert peer.locator(".game-shell").get_attribute("data-hand") == "left"
            assert peer.locator(".game-shell").get_attribute("data-control-size") == "large"
        assert not errors, errors
        print(
            f"{mode}: mobile client received desktop movement, bot and costume",
            flush=True,
        )
    finally:
        desktop.close()
        mobile.close()


if __name__ == "__main__":
    with sync_playwright() as driver:
        browser = driver.chromium.launch(
            executable_path=os.getenv("CHROMIUM_PATH") or None, args=["--no-sandbox"]
        )
        for mode in os.getenv("SMOKE_MODES", ",".join(MODES)).split(","):
            smoke(driver, browser, mode)
        browser.close()

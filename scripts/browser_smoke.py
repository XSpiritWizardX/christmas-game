"""Run against a built Snow Dash instance. Uses isolated, disposable guest rooms."""
import os
import re
from playwright.sync_api import sync_playwright

with sync_playwright() as driver:
    browser = driver.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH") or None, args=["--no-sandbox"])
    desktop = browser.new_context()
    mobile = browser.new_context(**driver.devices["Pixel 7"])
    host, peer = desktop.new_page(), mobile.new_page()
    errors = []
    for page in (host, peer):
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(os.getenv("SMOKE_URL","http://localhost:10000"))
    host.get_by_placeholder("Santa").fill("Snow QA")
    host.get_by_role("button",name="Create room").click()
    hud=host.locator(".hud-sub")
    hud.wait_for()
    code=re.search(r"Room (\w+)",hud.inner_text())[1]
    peer.get_by_placeholder("Santa").fill("Mobile QA")
    peer.get_by_placeholder("ABCD").fill(code)
    peer.get_by_role("button",name="Join room").tap()
    peer.locator(".hud-sub").wait_for()
    host.get_by_role("button",name="Menu",exact=True).click()
    host.get_by_label("Level",exact=True).select_option("boss")
    host.get_by_role("button",name="Yeti",exact=True).click()
    host.get_by_role("button",name="Add AI").click()
    host.get_by_role("button",name="Start game").click()
    host.get_by_role("button",name="Start round 1").click()
    for page in (host,peer):
        page.locator(".hud-title",has_text="North Pole Boss Battle").wait_for()
    host.keyboard.down("d")
    host.wait_for_timeout(250)
    host.keyboard.up("d")
    host.keyboard.press("Space")
    peer.get_by_role("button",name="Action",exact=True).tap()
    assert not errors, errors
    browser.close()
    print("Desktop host, mobile guest, character selection, AI, synchronized boss round and controls passed.")

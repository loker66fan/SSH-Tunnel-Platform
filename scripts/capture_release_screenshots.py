from __future__ import annotations

import asyncio
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

SCREENSHOT_DIR = ROOT / "assets" / "screenshots"
API_PORT = 18012
BASE_URL = f"http://127.0.0.1:{API_PORT}"


async def capture_web_screenshots() -> None:
    from playwright.async_api import async_playwright

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})

        await page.goto(BASE_URL, wait_until="networkidle")
        await page.locator("button").filter(has_text="登录").click()
        await page.locator("input").nth(0).fill("admin")
        await page.locator("input[type='password']").fill("admin")
        await page.locator("button").filter(has_text="登录").nth(1).click()
        await page.wait_for_timeout(1800)
        await page.screenshot(path=str(SCREENSHOT_DIR / "web-dashboard.png"), full_page=False)

        await page.goto(f"{BASE_URL}/audit.html", wait_until="networkidle")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=str(SCREENSHOT_DIR / "web-audit.png"), full_page=False)

        await page.goto(f"{BASE_URL}/terminal.html?tid=demo-terminal&user=admin", wait_until="networkidle")
        await page.screenshot(path=str(SCREENSHOT_DIR / "web-terminal.png"), full_page=True)
        await browser.close()


def capture_qt_screenshots() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    os.environ.setdefault(
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "--disable-gpu --disable-software-rasterizer --no-sandbox",
    )

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from apps.desktop.backend import BackendServerManager
    from apps.desktop.qt_app import DesktopWindow, LaunchChoiceWindow, LoginDialogWindow, _load_language_setting, _load_theme_setting

    app = QApplication.instance() or QApplication([])
    setattr(app, "_ssh_tunnel_language", _load_language_setting())
    setattr(app, "_ssh_tunnel_theme", _load_theme_setting())

    backend = BackendServerManager(base_host="127.0.0.1", port=API_PORT)

    launcher = LaunchChoiceWindow(backend)
    launcher.refresh_language()
    launcher.show()
    app.processEvents()
    launcher.grab().save(str(SCREENSHOT_DIR / "launcher.png"))

    login = LoginDialogWindow(backend, launcher=launcher)
    login.refresh_language()
    login.show()
    app.processEvents()
    login.grab().save(str(SCREENSHOT_DIR / "qt-login.png"))

    desktop = DesktopWindow(backend)
    desktop.current_user = "admin"
    desktop.client.set_auth("admin", "")
    desktop.sync_backend_base_url()
    desktop._show_workspace_view()
    desktop.refresh_dashboard()

    def shoot_workspace() -> None:
        app.processEvents()
        desktop.grab().save(str(SCREENSHOT_DIR / "qt-workspace.png"))
        desktop.close()
        login.close()
        launcher.close()
        backend.stop()
        app.quit()

    QTimer.singleShot(2500, shoot_workspace)
    app.exec()


def start_api_server() -> subprocess.Popen[str]:
    env = os.environ.copy()
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(API_PORT),
            "--log-level",
            "warning",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def wait_for_api(timeout: float = 12.0) -> None:
    import httpx
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = httpx.get(f"{BASE_URL}/openapi.json", timeout=1.0)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for API at {BASE_URL}")


def main() -> int:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    process = start_api_server()
    try:
        wait_for_api()
        capture_qt_screenshots()
        asyncio.run(capture_web_screenshots())
        print(f"Saved screenshots to {SCREENSHOT_DIR}")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except Exception:
            process.kill()


if __name__ == "__main__":
    raise SystemExit(main())

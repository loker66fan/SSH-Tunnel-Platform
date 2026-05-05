from __future__ import annotations

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


def capture_qt_screenshots() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    os.environ.setdefault(
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "--disable-gpu --disable-software-rasterizer --no-sandbox",
    )

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from qfluentwidgets import Theme, setTheme, setThemeColor

    from apps.desktop.backend import BackendServerManager
    from apps.desktop.qt_app import (
        ACCENT_COLOR,
        DesktopWindow,
        LaunchChoiceWindow,
        LoginDialogWindow,
        _load_language_setting,
        _save_theme_setting,
        apply_theme_palette,
    )

    app = QApplication.instance() or QApplication([])
    setattr(app, "_ssh_tunnel_language", _load_language_setting())
    _save_theme_setting(Theme.LIGHT)
    setattr(app, "_ssh_tunnel_theme", Theme.LIGHT)
    apply_theme_palette(Theme.LIGHT)
    setTheme(Theme.LIGHT)
    setThemeColor(ACCENT_COLOR)

    backend = BackendServerManager(base_host="127.0.0.1", port=API_PORT)

    launcher = LaunchChoiceWindow(backend)
    launcher.refresh_theme()
    launcher.refresh_language()
    launcher.show()
    app.processEvents()
    launcher.grab().save(str(SCREENSHOT_DIR / "launcher.png"))

    login = LoginDialogWindow(backend, launcher=launcher)
    login.refresh_theme()
    login.refresh_language()
    login.show()
    app.processEvents()
    login.grab().save(str(SCREENSHOT_DIR / "qt-login.png"))

    desktop = DesktopWindow(backend)
    desktop._theme = Theme.LIGHT
    desktop.apply_current_theme()
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

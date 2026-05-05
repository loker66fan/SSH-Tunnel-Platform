# SSH Tunnel Platform

SSH Tunnel Platform is a Python-based SSH tunnel management application that now provides both a Web dashboard and a Qt desktop workspace on top of the same FastAPI backend.

## Summary

- Desktop-first launcher with mode selection for Web and Qt
- Shared backend for tunnel management, SFTP browsing, MFA, audit logs, and Web terminal access
- User registration, per-user tunnel persistence, group management, and audit cleanup
- Bilingual UI foundation for Qt and Web (`zh-CN` / `en`)

## Current Release

- Version: `0.2.0`
- License: MIT
- Entry point: `python main.py`
- Web/API direct entry: `python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 18002`

## Primary Screens

- Launcher mode selection
- Qt tunnel workspace
- Web dashboard
- Audit log page
- Web terminal page

## Screenshot Assets

- `assets/screenshots/launcher.png`
- `assets/screenshots/qt-login.png`
- `assets/screenshots/qt-workspace.png`
- `assets/screenshots/web-dashboard.png`
- `assets/screenshots/web-audit.png`
- `assets/screenshots/web-terminal.png`

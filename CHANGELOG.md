# SSH 隧道平台 — 开发日志 & 使用说明

---

## 一、运行环境

| 组件 | 版本/要求 |
|------|----------|
| Python | 3.10+（当前开发使用 3.11.15） |
| 操作系统 | Linux / macOS / Windows (WSL) |
| pip | 随 Python 安装 |

### 依赖安装

```bash
# 进入项目目录
cd ssh_gateway_project_v2

# 一键安装所有依赖
pip install -r requirements.txt
```

### 依赖清单

| 包 | 用途 |
|----|------|
| `fastapi` | Web API 框架（控制层） |
| `uvicorn` | ASGI 服务器 |
| `asyncssh` | SSH 协议实现（隧道 + 终端） |
| `aiosqlite` | 异步 SQLite 数据库 |
| `bcrypt` | 密码哈希（认证） |
| `pyotp` | TOTP 生成与验证（MFA） |
| `qrcode` | QR 码生成（MFA 扫码绑定） |
| `Pillow` | qrcode 图片渲染依赖 |
| `httpx` | SOCKS5 验证用的 HTTP 客户端 |
| `websockets` | WebSocket 终端通信 |

### 前端（CDN，无需本地安装）

| 库 | 版本 | 用途 |
|----|------|------|
| TailwindCSS | 3.x | UI 样式 |
| Alpine.js | 3.x | 响应式数据绑定 |
| xterm.js | 4.17 | 浏览器终端模拟器 |

---

## 二、快速启动

```bash
# 1. 进入项目目录
cd ssh_gateway_project_v2

# 2. 安装依赖（首次运行）
pip install -r requirements.txt

# 3. 启动 API 服务器
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 18002

# 4. 打开浏览器访问
# http://localhost:18002
```

---

## 三、使用方式

### 3.1 注册与登录

1. 打开 `http://localhost:18002`
2. 点击"注册"按钮，输入用户名和密码
3. 点击"登录"，输入凭据

### 3.2 启用 MFA（可选）

1. 登录后，点击导航栏的"启用 MFA"按钮
2. 弹出窗口显示 QR 码（可在手机 TOTP 应用中扫描，如 Google Authenticator、Microsoft Authenticator、Authy 等）
3. 在"验证码"输入框中，输入手机 App 上的 6 位数字
4. 点击"验证并激活"
5. 看到"MFA 验证成功并已启用！"提示即完成

### 3.3 创建 SSH 隧道

1. 点击"新建隧道"按钮
2. 填写隧道信息：
   - **隧道名称**：自定义名称
   - **SSH 主机**：目标 SSH 服务器的 IP 地址
   - **SSH 端口**：默认 22
   - **SSH 用户名**：SSH 登录用户名
   - **SSH 密码**：SSH 登录密码
   - **本地端口**：本机监听端口（如 8080）
   - **远程主机**：要转发到的远程地址
   - **远程端口**：要转发到的远程端口
   - **类型**：`local`（本地端口转发）或 `socks5`（SOCKS5 动态代理）
3. 点击"创建隧道"

### 3.4 管理隧道

- **查看状态**：隧道列表显示所有活动隧道，带颜色状态指示
- **验证隧道**：点击"验证"按钮检查隧道连通性
- **修改隧道**：点击"修改"按钮编辑隧道参数（远程主机/端口可热更新）
- **打开终端**：点击"终端"按钮进入交互式 SSH 终端
- **停止隧道**：点击"停止"按钮关闭隧道

### 3.5 使用 Web SSH 终端

1. 在活动隧道列表中，点击"终端"按钮
2. 跳转到终端页面，等待连接建立
3. 看到命令行提示后，即可输入命令（如 `ls -l`, `pwd`, `top` 等）
4. 终端支持：
   - 实时输入/输出双向通信
   - 彩色输出（ANSI 转义码）
   - Ctrl+C 中断命令
   - `exit` 退出 shell
5. 关闭页面或点击"返回仪表盘"结束终端会话

---

## 四、项目结构

```
ssh_gateway_project_v2/
├── apps/api/           # 控制层（FastAPI）
│   ├── main.py         # API 入口点、路由注册、静态文件服务
│   └── routes/         # API 路由
│       ├── auth.py     # 认证（注册/登录/MFA）
│       ├── tunnel.py   # 隧道管理（CRUD + WebSocket 终端）
│       └── admin.py    # 管理接口
├── services/           # 业务逻辑层
│   └── tunnel_service.py  # 隧道服务（ACL 校验 + 审计 + 调用模块）
├── modules/            # 核心模块
│   ├── ssh/
│   │   ├── base.py         # SSH 后端抽象接口
│   │   └── asyncssh_backend.py  # AsyncSSH 实现（连接/隧道/PTY shell）
│   ├── tunnel/
│   │   └── manager.py      # 隧道管理器（端口转发/SOCKS5/终端会话）
│   ├── auth/
│   │   ├── password.py     # 密码认证
│   │   └── mfa/
│   │       ├── base.py     # MFA 抽象接口
│   │       └── totp.py     # TOTP 实现
│   ├── acl/
│   │   ├── policy.py       # ACL 策略定义
│   │   └── evaluator.py    # ACL 评估器
│   └── audit/
│       ├── logger.py       # 审计日志记录器
│       └── models.py       # 审计日志数据模型
├── infra/db/
│   └── sqlite.py       # SQLite 数据库（用户/隧道/审计存储）
├── core/
│   ├── config.py       # 全局配置（Pydantic Settings）
│   └── logger.py       # 日志配置
├── web/                # 前端静态页面
│   ├── index.html      # 仪表盘（登录/注册/隧道管理/MFA）
│   └── terminal.html   # Web SSH 终端页面（xterm.js）
├── requirements.txt    # Python 依赖
└── CHANGELOG.md        # 本文件
```

---

## 五、开发日志

### 2026-04-27：Web SSH 终端功能

**目标**：为 SSH 隧道平台添加基于 Web 的交互式 SSH 终端，仿照 Windows Terminal 体验。

**实现步骤**：

1. **后端 PTY 支持**
   - 在 [asyncssh_backend.py](./modules/ssh/asyncssh_backend.py#L114-L127) 中新增 `open_shell()` 方法
   - 使用 `asyncssh` 的 `create_process('bash')` 创建带 PTY 的交互式 shell
   - 显式指定 `stdin/stdout/stderr=asyncssh.PIPE` 确保流正确初始化

2. **WebSocket 双向通信**
   - 新增 WebSocket 路由 `/tunnel/ws/terminal/{tunnel_id}`（见 [routes/tunnel.py](./apps/api/routes/tunnel.py#L112-L124)）
   - 使用 `asyncio.wait()` 并发读写，`FIRST_COMPLETED` 策略避免互相影响

3. **前端终端渲染**
   - 集成 `xterm.js` 4.17 + `FitAddon` 自适应终端窗口
   - 彩色输出支持（ANSI escape codes）
   - 深色主题匹配 Windows Terminal 风格

4. **编辑隧道弹窗增强**
   - 修改弹窗显示所有字段（SSH 用户名/密码/本地端口/远程主机/端口/类型）
   - 本地端口和类型字段设为只读

**遇到的 Bug 及修复**：

| # | Bug | 根因 | 修复方案 |
|---|-----|------|---------|
| 1 | 终端无任何显示 | WebSocket 不支持自定义 `X-User` 请求头 | 改用 URL 查询参数 `?user=xxx` 传参认证 |
| 2 | `create_process()` 报 `unexpected keyword argument 'width'` | 参数名错误，AsyncSSH 需要 `term_size=(w,h)` | 替换为正确的参数名 |
| 3 | 终端连接后立即断开 | `SSHWriter.write()` 是同步方法，错误地使用了 `await`，导致 `NoneType` 错误 | 改为同步调用 `write()` + `await drain()` |
| 4 | `'str' object has no attribute 'decode'` | PTY 模式返回数据已是 `str`，无需 `.decode()` | 添加 `isinstance(data, bytes)` 判断后再 decode |
| 5 | MFA 启用失败 `No module named 'PIL'` | `qrcode` 生成图片依赖 `Pillow`，环境中未安装 | `pip install Pillow` |

### 2026-04-27：隧道修改功能 & 验证状态修复

**Bug 修复**：

| # | Bug | 根因 | 修复方案 |
|---|-----|------|---------|
| 6 | 修改隧道后 SSH 配置未生效 | `update_tunnel` 只更新了内存属性，未重建 SSH 连接和隧道 | 重写为停止旧隧道 → 用新参数重建 SSH 连接和隧道（保留原 tunnel_id） |
| 7 | 验证状态图标始终红色 | `socket.connect_ex` 与 asyncssh 隧道存在兼容性问题，端口检测不可靠 | 改用 `backend._conn.is_closed()` 直接检查 SSH 连接存活状态 |
| 8 | 编辑弹窗字段映射错误 | list API 返回 `ssh_username` 但前端读取 `username` | 统一字段名并补全 `password`/`remote_host`/`remote_port` 返回 |

**功能改进**：

- **AsyncSSHBackend**：新增 `local_port`/`remote_host`/`remote_port` 配置存储及 `password` 属性暴露
- **TunnelManager.create**：创建时将完整配置传入 `AsyncSSHBackend` 存储
- **TunnelManager.verify_tunnel**：改用 SSH 连接存活检测（终端能用即验证通过）
- **隧道列表 API**：直接返回 backend 存储的 `local_port`/`remote_host`/`remote_port`/`username`/`password`
- **前端验证图标**：三状态逻辑 — 🟢 绿色（SSH 连接正常）、🟡 黄色闪烁（检测中）、🔴 红色（连接失败）
- **移除延迟显示**：图标颜色直接反映可用性，不再显示毫秒数

### 2026-04-27：基础功能实现

- 密码认证（bcrypt 哈希存储）
- 本地端口转发、SOCKS5 动态代理
- MFA（TOTP）绑定与验证（QR 码 + 验证码）
- ACL 访问控制
- 审计日志（登录/隧道创建/命令执行）
- SQLite 持久化存储
- 基于 TailwindCSS + Alpine.js 的 Web 仪表盘

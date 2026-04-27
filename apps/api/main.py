
import sys
import os
from pathlib import Path

# 将项目根目录添加到 sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apps.api.routes import auth, tunnel, admin
from infra.db.sqlite import db
from core.config import settings
from modules.acl.evaluator import acl_evaluator
import asyncio

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init()
    # Load ACL policies
    await acl_evaluator.load_policies()
    yield
    await db.close()

app = FastAPI(title="SSH Tunnel Platform API", lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tunnel.router, prefix="/tunnel", tags=["tunnel"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

# Serve static files
app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)

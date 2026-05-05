
from fastapi import APIRouter, HTTPException, Header, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from services.tunnel_service import tunnel_service
from typing import Optional
from core.logger import logger

router = APIRouter()

class TunnelCreateRequest(BaseModel):
    ssh_host: str
    ssh_port: int = 22
    username: str
    password: str
    local_port: int
    remote_host: Optional[str] = None
    remote_port: Optional[int] = None
    type: str = "local" # local, socks5
    remark: Optional[str] = None
    group_name: Optional[str] = None

@router.post("/create")
async def create_tunnel(req: TunnelCreateRequest, x_user: str = Header("user")):
    try:
        tid = await tunnel_service.create_tunnel(x_user, req.model_dump())
        return {"tunnel_id": tid}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_tunnels(x_user: str = Header("user")):
    tunnels_info = await tunnel_service.list_tunnels(x_user)
    logger.info(f"Listing tunnels for {x_user}, count: {len(tunnels_info)}")
    return {"tunnels": tunnels_info}

@router.get("/groups")
async def list_tunnel_groups(x_user: str = Header("user")):
    groups = await tunnel_service.list_tunnel_groups(x_user)
    return {"groups": groups}

@router.post("/start/{tunnel_id}")
async def start_tunnel(tunnel_id: str, x_user: str = Header("user")):
    try:
        success = await tunnel_service.start_tunnel(x_user, tunnel_id)
        if success:
            return {"message": "Tunnel started"}
        raise HTTPException(status_code=404, detail="Tunnel not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify/{tunnel_id}")
async def verify_tunnel(tunnel_id: str, local_port: int, x_user: str = Header("user")):
    try:
        return await tunnel_service.verify_tunnel(x_user, tunnel_id, local_port)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop/{tunnel_id}")
async def stop_tunnel(tunnel_id: str, x_user: str = Header("user")):
    if await tunnel_service.stop_tunnel(x_user, tunnel_id):
        return {"message": "Tunnel stopped"}
    raise HTTPException(status_code=404, detail="Tunnel not found")

@router.delete("/{tunnel_id}")
async def delete_tunnel(tunnel_id: str, x_user: str = Header("user")):
    if await tunnel_service.delete_tunnel(x_user, tunnel_id):
        return {"message": "Tunnel deleted"}
    raise HTTPException(status_code=404, detail="Tunnel not found")

class CommandRequest(BaseModel):
    command: str

class TunnelUpdateRequest(BaseModel):
    remark: Optional[str] = None
    group_name: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    local_port: Optional[int] = None
    remote_host: Optional[str] = None
    remote_port: Optional[int] = None
    type: Optional[str] = None

class LogoutRequest(BaseModel):
    save_tunnels: bool = True

class TunnelGroupRenameRequest(BaseModel):
    old_group_name: str
    new_group_name: str

class TunnelGroupClearRequest(BaseModel):
    group_name: str

@router.post("/exec/{tunnel_id}")
async def exec_command(tunnel_id: str, req: CommandRequest, x_user: str = Header("user")):
    try:
        output = await tunnel_service.run_command(x_user, tunnel_id, req.command)
        return {"output": output}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update/{tunnel_id}")
async def update_tunnel(tunnel_id: str, req: TunnelUpdateRequest, x_user: str = Header("user")):
    try:
        success = await tunnel_service.update_tunnel(
            x_user, tunnel_id, 
            req.remark, req.group_name, req.ssh_host, req.ssh_port,
            req.username, req.password, req.local_port,
            req.remote_host, req.remote_port, req.type
        )
        if success:
            return {"message": "Tunnel updated successfully"}
        raise HTTPException(status_code=404, detail="Tunnel not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/groups/rename")
async def rename_tunnel_group(req: TunnelGroupRenameRequest, x_user: str = Header("user")):
    try:
        changed_count = await tunnel_service.rename_tunnel_group(
            x_user, req.old_group_name, req.new_group_name
        )
        return {"message": "Group renamed", "changed_count": changed_count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/groups/clear")
async def clear_tunnel_group(req: TunnelGroupClearRequest, x_user: str = Header("user")):
    try:
        changed_count = await tunnel_service.clear_tunnel_group(x_user, req.group_name)
        return {"message": "Group cleared", "changed_count": changed_count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logout")
async def logout(req: LogoutRequest, x_user: str = Header("user")):
    try:
        await tunnel_service.logout_user(x_user, req.save_tunnels)
        return {"message": "Logout successful"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/terminal/{tunnel_id}")
async def websocket_terminal(websocket: WebSocket, tunnel_id: str, user: str = "user"):
    await websocket.accept()
    try:
        await tunnel_service.open_terminal_session(user, tunnel_id, websocket)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for tunnel {tunnel_id}")
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
    except Exception as e:
        logger.error(f"WebSocket error for tunnel {tunnel_id}: {e}")
        await websocket.close(code=1011, reason=str(e))

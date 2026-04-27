
from fastapi import APIRouter, HTTPException, Header, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from services.tunnel_service import tunnel_service
from modules.tunnel.manager import tunnel_manager
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

@router.post("/create")
async def create_tunnel(req: TunnelCreateRequest, x_user: str = Header("user")):
    try:
        tid = await tunnel_service.create_tunnel(x_user, req.model_dump())
        return {"tunnel_id": tid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_tunnels():
    tunnels_info = []
    # debug log
    logger.info(f"Listing tunnels, count: {len(tunnel_manager._active_tunnels)}")
    
    for tid, backend in tunnel_manager._active_tunnels.items():
        # Get the first tunnel's local port (MVP assumes one listener per backend)
        local_port = 0
        if backend._tunnels:
            # asyncssh listener object
            # Note: For SOCKS5, it might be a list of listeners
            listener = backend._tunnels[0]
            try:
                if hasattr(listener, 'get_port'):
                    local_port = listener.get_port()
                elif hasattr(listener, 'get_extra_info'):
                    addr = listener.get_extra_info('sockname')
                    if addr:
                        local_port = addr[1]
            except:
                pass
        
        # Determine tunnel type
        is_socks = hasattr(backend, '_is_socks') and backend._is_socks
        
        tunnels_info.append({
            "id": tid,
            "local_port": local_port,
            "type": "socks5" if is_socks else "local",
            "ssh_host": backend.host,
            "ssh_port": backend.port,
            "ssh_username": backend.username,
            "remark": backend.remark
        })
    return {"tunnels": tunnels_info}

@router.post("/verify/{tunnel_id}")
async def verify_tunnel(tunnel_id: str, local_port: int, x_user: str = Header("user")):
    try:
        success = await tunnel_service.verify_tunnel(x_user, tunnel_id, local_port)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop/{tunnel_id}")
async def stop_tunnel(tunnel_id: str, x_user: str = Header("user")):
    if await tunnel_service.stop_tunnel(x_user, tunnel_id):
        return {"message": "Tunnel stopped"}
    raise HTTPException(status_code=404, detail="Tunnel not found")

class CommandRequest(BaseModel):
    command: str

class TunnelUpdateRequest(BaseModel):
    remark: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    local_port: Optional[int] = None
    remote_host: Optional[str] = None
    remote_port: Optional[int] = None
    type: Optional[str] = None

@router.post("/exec/{tunnel_id}")
async def exec_command(tunnel_id: str, req: CommandRequest, x_user: str = Header("user")):
    try:
        output = await tunnel_service.run_command(x_user, tunnel_id, req.command)
        return {"output": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update/{tunnel_id}")
async def update_tunnel(tunnel_id: str, req: TunnelUpdateRequest, x_user: str = Header("user")):
    try:
        success = await tunnel_service.update_tunnel(
            x_user, tunnel_id, 
            req.remark, req.ssh_host, req.ssh_port,
            req.username, req.password, req.local_port,
            req.remote_host, req.remote_port, req.type
        )
        if success:
            return {"message": "Tunnel updated successfully"}
        raise HTTPException(status_code=404, detail="Tunnel not found")
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

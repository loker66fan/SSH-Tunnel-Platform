
import asyncio
from modules.tunnel.manager import tunnel_manager

async def test():
    print("Creating tunnel...")
    try:
        tid = await tunnel_manager.create_local_forward(
            host="127.0.0.1",
            port=2222,
            username="user",
            password="pass",
            local_port=10080,
            remote_host="127.0.0.1",
            remote_port=2222
        )
        print(f"Tunnel created: {tid}")
        await asyncio.sleep(5)
        print("Stopping tunnel...")
        await tunnel_manager.stop_tunnel(tid)
        print("Done")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())

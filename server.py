
import asyncio
import uvicorn
from storage import Storage
from api import app

async def main():
    s = Storage()
    await s.init()
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())

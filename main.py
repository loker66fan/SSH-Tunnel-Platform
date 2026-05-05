import uvicorn

from apps.api.main import app
from core.config import settings


if __name__ == "__main__":
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)

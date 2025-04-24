from fastapi import FastAPI

from app.core.config import settings
from app.middlewares import setup_middlewares
from app.api import setup_routers


def create_app() -> FastAPI:
    _app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESC,
        version=settings.APP_VERSION,
        docs_url=None,
        middleware=setup_middlewares(),
    )

    setup_routers(_app)
    return _app


app = create_app()

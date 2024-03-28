import logging
from typing import Awaitable, Callable

import fastapi

# from dataline.api.connection.router import router as connection_router
from dataline.api.settings.router import router as settings_router
from dataline.repositories.base import NotFoundError
from fastapi import Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def catch_exceptions_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        return await call_next(request)
    except NotFoundError as e:
        # No need to log these, expected errors
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": e.message})


def handle_exception(request: Request, e: Exception) -> JSONResponse:
    logger.exception(e)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": str(e)})


class App(fastapi.FastAPI):
    def __init__(self) -> None:
        super().__init__(title="Dataline API")
        self.middleware("http")(catch_exceptions_middleware)
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.include_router(settings_router)
        # self.include_router(connection_router)

        # Handle 500s separately to play well with TestClient and allow re-raising in tests
        self.add_exception_handler(Exception, handle_exception)

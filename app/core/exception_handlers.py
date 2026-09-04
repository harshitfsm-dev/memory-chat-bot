import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.db.errors import PersistenceError

logger = logging.getLogger(__name__)


async def persistence_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Translate a failed write into a retryable response.

    Write failures are cross-cutting: users, auth, and chat can all hit them.
    Handling them once here keeps every router from repeating the same mapping,
    and keeps the database cause out of the response body.
    """
    logger.error(
        "Persistence failure on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "The request could not be stored. Please retry."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(PersistenceError, persistence_error_handler)

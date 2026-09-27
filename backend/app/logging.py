"""Application logging configuration."""

import logging
import sys
from pythonjsonlogger import jsonlogger
import uuid
from contextvars import ContextVar

# Context variable to store the request ID for the current context
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDFilter(logging.Filter):
    """Filter to inject request ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def configure_logging() -> None:
    """Configure application logging."""
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create a handler that writes to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    # Create a JSON formatter
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s"
    )
    handler.setFormatter(formatter)

    # Add the request ID filter
    handler.addFilter(RequestIDFilter())

    # Add the handler to the logger
    logger.addHandler(handler)

    # Prevent duplicate logs in Uvicorn
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False


def get_request_id() -> str:
    """Get the current request ID from the context."""
    return request_id_ctx.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in the context."""
    request_id_ctx.set(request_id)
import logging
from datetime import datetime, timezone

from langchain_core.tools import tool


logger = logging.getLogger(__name__)


@tool
def get_current_utc_time() -> str:
    """Return the current date and time in UTC using ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def handle_tool_error(error: Exception) -> str:
    logger.error(
        "Agent tool execution failed",
        exc_info=(type(error), error, error.__traceback__),
    )
    return "The tool could not complete the request."


AGENT_TOOLS = [get_current_utc_time]

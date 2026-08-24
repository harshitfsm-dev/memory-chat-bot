import logging
from datetime import datetime, timezone
from langchain.agents.middleware import ToolCallRequest
from langchain_core.tools import tool, ToolException


logger = logging.getLogger(__name__)


@tool
def get_current_utc_time() -> str:
    """Return the current date and time in UTC using ISO 8601 format."""
    logger.info(
        "Agent tool get_current_utc_time called",
    )
    raise Exception("Sorry, Date library is not available.")
    return datetime.now(timezone.utc).isoformat()


def handle_tool_error(error: Exception, request: ToolCallRequest) -> str:
    """Turn a tool failure into a generic error message for the model.

    The real exception is logged server-side only, so internal details never
    reach the model or the end user.
    """
    logger.error(
        "Agent tool execution failed: %s",
        request.tool_call["name"],
        # exc_info=(type(error), error, error.__traceback__),
    )
    return ValueError("The tool could not complete the request.")


AGENT_TOOLS = [get_current_utc_time]

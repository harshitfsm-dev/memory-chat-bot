import logging
from datetime import datetime, timezone

from langchain.agents.middleware import ToolCallRequest
from langchain_core.tools import tool


logger = logging.getLogger(__name__)


@tool
def get_current_utc_time() -> str:
    """Return the current date and time in UTC using ISO 8601 format."""
    logger.info("Agent tool get_current_utc_time called")
    return datetime.now(timezone.utc).isoformat()


def handle_tool_error(error: Exception, request: ToolCallRequest) -> str:
    """Return a safe tool error to the model without exposing internals."""
    logger.error(
        "Agent tool execution failed: %s (%s)",
        request.tool_call["name"],
        type(error).__name__,
    )
    return "The tool could not complete the request."


AGENT_TOOLS = [get_current_utc_time]

"""One read-only domain connection for the introductory specialist."""
import logging
import os
import time
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

_client = None
_tools = []
logger = logging.getLogger(__name__)


def start_clients():
    global _client, _tools
    endpoint = os.environ['MCP_CLUSTER_URL'].rstrip('/') + '/mcp'
    for attempt in range(1, 16):
        candidate = MCPClient(lambda: streamablehttp_client(endpoint))
        try:
            candidate.start()
            _tools = candidate.list_tools_sync()
            _client = candidate
            return
        except Exception:
            try:
                candidate.stop(None, None, None)
            except Exception:
                pass
            if attempt == 15:
                raise
            logger.warning("Kubernetes MCP is not ready; retrying (%s/15)", attempt)
            time.sleep(2)


def stop_clients():
    global _client
    if _client is not None:
        _client.stop(None, None, None)
        _client = None


def cluster_tools():
    return list(_tools)

"""Test MCPClient initialization and session management."""
from datahub_rail.client import MCPClient


def test_client_init_with_server_params():
    """MCPClient can be initialized with MCP server command."""
    client = MCPClient(
        command="uvx",
        args=["mcp-server-datahub@latest"],
    )
    assert client is not None
    assert client.command == "uvx"
    assert client.args == ["mcp-server-datahub@latest"]


def test_client_init_defaults():
    """MCPClient can be initialized with minimal params."""
    client = MCPClient()
    assert client is not None


def test_client_context_manager():
    """MCPClient supports context manager protocol."""
    with MCPClient() as client:
        assert client is not None

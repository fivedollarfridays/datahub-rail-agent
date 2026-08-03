"""Network block that keeps the suite honest.

Every test in this repo runs against recorded responses and stubs. That is
only meaningful if it is enforced: a developer machine with the DataHub
quickstart running will otherwise let a test reach a real service, and a
fail-soft handler will hide the difference until CI — which has no service —
disagrees. Sockets are blocked for every test; ``@pytest.mark.allow_network``
is the deliberate, visible escape hatch.
"""
import socket


class NetworkBlocked(RuntimeError):
    """A test tried to open a socket. Suites here run on recorded data."""


def _blocked(*args, **kwargs):
    """Stand-in for every socket entry point."""
    raise NetworkBlocked(
        "network access is blocked in this suite — stub the collaborator, or"
        " mark the test @pytest.mark.allow_network if a live call is the point"
    )


def install(monkeypatch) -> None:
    """Block the socket entry points aiohttp and stdlib clients bottom out in."""
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)

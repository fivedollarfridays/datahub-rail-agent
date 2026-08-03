"""Canary: prove the network block is real, not a no-op.

A fail-soft code path plus a service running on the developer's machine is
how a broken test passes locally and fails in CI — the exception the test
should have hit gets swallowed, the assertion is never reached, and the green
bar means nothing. The suite therefore blocks sockets outright. These tests
exist to validate the guard itself: if they ever pass because nothing is
being blocked, the guard has silently stopped working.
"""
import asyncio
import socket

import aiohttp
import pytest

from tests.hermetic import NetworkBlocked

GMS = "http://localhost:8080/openapi/v3/entity/dataset?count=1"


def test_raw_socket_connect_is_blocked():
    """The primitive every HTTP client bottoms out in is unavailable."""
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("localhost", 8080), timeout=1)


def test_name_resolution_is_blocked():
    """Blocking connect alone leaves resolvers that dial by IP; block both."""
    with pytest.raises(NetworkBlocked):
        socket.getaddrinfo("localhost", 8080)


def test_aiohttp_cannot_reach_a_live_local_gms():
    """The real client, against the real quickstart URL, cannot get through.

    On a machine with DataHub running this is the test that matters: it fails
    if the guard leaks, which is exactly the condition that made a mocked
    write-back test pass locally and fail in CI.
    """

    async def attempt():
        async with aiohttp.ClientSession() as session:
            async with session.get(GMS, timeout=aiohttp.ClientTimeout(total=5)):
                pass

    with pytest.raises((aiohttp.ClientError, NetworkBlocked, OSError)):
        asyncio.run(attempt())


@pytest.mark.allow_network
def test_opt_out_marker_restores_sockets():
    """The escape hatch works, so a deliberate live smoke stays possible."""
    with pytest.raises(OSError) as excinfo:
        socket.create_connection(("127.0.0.1", 1), timeout=0.2)

    assert not isinstance(excinfo.value, NetworkBlocked)

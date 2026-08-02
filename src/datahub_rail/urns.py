"""Helpers for reading DataHub dataset URNs.

A dataset URN looks like::

    urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.users,PROD)
"""

_PLATFORM_MARKER = "urn:li:dataPlatform:"


def name_from_urn(urn: str) -> str:
    """Derive the table name from a dataset URN."""
    if "," in urn:
        return urn.split(",")[1].split(".")[-1]
    return urn


def platform_from_urn(urn: str) -> str:
    """Derive the data platform from a dataset URN."""
    if _PLATFORM_MARKER in urn:
        return urn.split(_PLATFORM_MARKER, 1)[1].split(",")[0]
    return "unknown"


def platform_urn_from_dataset(urn: str, default: str = "urn:li:dataPlatform:postgres") -> str:
    """Derive the data platform URN from a dataset URN."""
    if _PLATFORM_MARKER in urn:
        return _PLATFORM_MARKER + urn.split(_PLATFORM_MARKER, 1)[1].split(",")[0]
    return default

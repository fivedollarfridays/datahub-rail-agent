"""Type definitions for DataHub context graph entities."""
from dataclasses import dataclass


@dataclass
class Dataset:
    """DataHub dataset metadata."""

    urn: str
    name: str
    platform: str
    owner: str
    last_modified: int


@dataclass
class Field:
    """Dataset schema field."""

    field_path: str
    type: str
    description: str


@dataclass
class Lineage:
    """Lineage node in upstream/downstream walk."""

    urn: str
    name: str
    platform: str


@dataclass
class Freshness:
    """Dataset freshness metadata."""

    urn: str
    last_modified: int
    is_stale: bool
    expected_frequency: int


@dataclass
class SchemaMetadata:
    """Dataset schema with fields and description."""

    urn: str
    fields: list[dict]
    description: str


@dataclass
class LineageResult:
    """Upstream/downstream lineage for a dataset."""

    urn: str
    upstream: list[dict]
    downstream: list[dict]

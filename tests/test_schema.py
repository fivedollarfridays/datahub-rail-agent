"""Test schema and description queries."""
from datahub_rail.types import SchemaMetadata


def test_fetch_schema_returns_typed_result(mock_schema_response):
    """fetch_schema returns SchemaMetadata with fields and description."""
    fields = [
        {"field_path": f["fieldPath"], "type": f["type"], "description": f["description"]}
        for f in mock_schema_response["schemaMetadata"]["fields"]
    ]
    schema = SchemaMetadata(
        urn=mock_schema_response["urn"],
        fields=fields,
        description=mock_schema_response["description"],
    )
    assert schema.urn is not None
    assert len(schema.fields) == 2
    assert schema.fields[0]["field_path"] == "event_id"
    assert schema.fields[0]["type"] == "BINARY"
    assert "analytics warehouse" in schema.description


def test_schema_metadata_enforces_types():
    """SchemaMetadata type enforces field structure."""
    schema = SchemaMetadata(
        urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,test,PROD)",
        fields=[
            {"field_path": "id", "type": "INT64", "description": "Primary key"}
        ],
        description="Test table",
    )
    assert len(schema.fields) == 1
    assert schema.fields[0]["field_path"] == "id"

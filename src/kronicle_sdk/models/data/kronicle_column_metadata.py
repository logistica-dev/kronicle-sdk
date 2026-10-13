# kronicle_sdk/models/data/kronicle_column_metadata.py
"""Per-column annotations carried by a :class:`KronicleChannel`.

Mirrors the server's ``ColumnMetadata``: a mapping of *DB column name* to a small
set of descriptive descriptors. Keys are the channel's normalized column names
(the ones from ``channel_schema``), never user-facing aliases.

    {
      "temperature": {"unit": "Cel", "description": "Air temperature"},
      "humidity": {"unit": "%"}
    }

Descriptive fields are mutable labels: they never affect the channel's data
schema (column names/types stay immutable). Unknown descriptors are accepted
(``extra="allow"``) so the wire format can grow without an SDK release.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KronicleColumnMetadata(BaseModel):
    """Descriptive annotations for a single channel column.

    All fields are optional; unknown descriptors are preserved.
    """

    model_config = ConfigDict(extra="allow")

    unit: str | None = Field(default=None, max_length=64, description="Physical unit, e.g. 'Cel' (UCUM) or 'C'")
    description: str | None = Field(default=None, max_length=4096, description="Free-text description")
    ontology: str | None = Field(default=None, max_length=512, description="URI/IRI to an external ontology term")

    def to_json(self) -> dict[str, Any]:
        """Serializable form: drop unset known keys, keep every extra."""
        return self.model_dump(mode="json", exclude_none=True)


#: Mapping of normalized DB column name -> :class:`KronicleColumnMetadata`.
ColumnMetadataMap = dict[str, KronicleColumnMetadata]

#: Accepted input for a single column entry: either the typed model or a raw
#: ``{"unit": ..., "description": ...}`` dict (coerced to :class:`KronicleColumnMetadata`).
ColumnMetadataInput = KronicleColumnMetadata | dict[str, Any]


if __name__ == "__main__":  # pragma: no cover
    from kronicle_sdk.utils.log import log_d

    here = "KronicleColumnMetadata"
    log_d(here, "basic", KronicleColumnMetadata(unit="Cel", description="Air temperature").to_json())
    log_d(here, "extras", KronicleColumnMetadata(unit="%", precision=2).to_json())  # type: ignore[reportCallIssue]
    log_d(here, "empty", KronicleColumnMetadata().to_json())

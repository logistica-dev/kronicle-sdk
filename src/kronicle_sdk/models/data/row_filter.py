# kronicle_sdk/models/data/row_filter.py
"""SDK-side row query filter for channel row/column endpoints.

Maps filter fields onto the URL query parameters expected by the server's
row endpoints (see server `RowQueryFilter` / `RowRequestFilter`):

    ?col[name]=Tintin&min[time]=2026-03-20&max[time]=2026-03-21
    &any[tag]=room1,room2&has[status]=ok,fail
    &sort=target,-time&columns=time,value&limit=100&offset=0&skip_received=false&strict=false

Column names are validated and normalized client-side so that invalid input
raises a clear, local error instead of surfacing late on the server.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from kronicle_sdk.utils.str_utils import (
    normalize_name,
    normalize_name_keep_dots,
    normalize_sort_name,
    split_strip,
)

MAX_LIMIT = 500
MAX_OFFSET = 10_000


class RowFilter(BaseModel):
    """Declarative filter for fetching rows of a channel.

    Only fields that are set are sent to the server, so an empty `RowFilter()`
    yields no query parameters at all.
    """

    limit: int | None = Field(default=None, ge=1, description="Max number of rows to return")
    offset: int | None = Field(default=None, ge=0, description="Number of rows to skip (pagination)")
    sort: list[str] | str | None = Field(
        default=None,
        description="Sort columns; prefix with '-' for descending order. May be a list or a comma-separated string.",
    )

    columns: list[str] | str | None = Field(
        default=None, description="Columns to include in the result (list or comma-separated string)"
    )
    skip_received: bool | None = Field(default=None, description="False to include the reception timestamp column")

    col: dict[str, str] | None = Field(
        default=None, description="Exact match filters: {'name': 'Tintin'} -> ?col[name]=Tintin"
    )
    min: dict[str, str] | None = Field(
        default=None, description="Minimum value filters: {'time': '2026-03-20'} -> ?min[time]=..."
    )
    max: dict[str, str] | None = Field(
        default=None, description="Maximum value filters: {'time': '2026-03-21'} -> ?max[time]=..."
    )
    any: dict[str, list[str]] | None = Field(
        default=None, description="Multi-value filters: {'tag': ['room1','room2']} -> ?any[tag]=..."
    )
    has: dict[str, list[str]] | None = Field(
        default=None, description="Multi-value presence filters: {'status': ['ok','fail']} -> ?has[...]=..."
    )

    strict: bool | None = Field(
        default=None, description="Raise server-side errors if true, otherwise accumulate warnings"
    )

    @field_validator("limit")
    @classmethod
    def _cap_limit(cls, v):
        if v is None:
            return v
        return min(v, MAX_LIMIT)

    @field_validator("offset")
    @classmethod
    def _cap_offset(cls, v):
        if v is None:
            return v
        return min(v, MAX_OFFSET)

    @field_validator("sort")
    @classmethod
    def _norm_sort(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return split_strip(v, ",", normalize_sort_name) or None
        result: list[str] = []
        for s in v:
            result.extend(split_strip(s, ",", normalize_sort_name))
        return result or None

    @field_validator("columns")
    @classmethod
    def _norm_columns(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return split_strip(v, ",", normalize_name) or None
        return [normalize_name(c) for c in v] or None

    @field_validator("col")
    @classmethod
    def _norm_col(cls, v):
        return {normalize_name_keep_dots(k): val for k, val in v.items()} if v else v

    @field_validator("min", "max")
    @classmethod
    def _norm_min_max(cls, v):
        return {normalize_name(k): val for k, val in v.items()} if v else v

    @field_validator("any")
    @classmethod
    def _norm_any(cls, v):
        if not v:
            return v
        return {normalize_name_keep_dots(k): split_strip_i(vals) for k, vals in v.items()}

    @field_validator("has")
    @classmethod
    def _norm_has(cls, v):
        if not v:
            return v
        return {normalize_name(k): split_strip_i(vals) for k, vals in v.items()}

    def model_dump(self, *args, exclude_none=True, **kwargs) -> dict:
        return super().model_dump(*args, exclude_none=exclude_none, **kwargs)

    def to_params(self) -> dict[str, Any]:  # noqa: C901
        """Return a `requests`-compatible query-parameters dict.

        Only set fields are included. Bracket keys (e.g. ``col[name]``) are
        emitted so the server can decode them back into its bracketed filters.
        """
        params: dict[str, Any] = {}

        if self.limit is not None:
            params["limit"] = self.limit
        if self.offset is not None:
            params["offset"] = self.offset
        if self.sort is not None:
            params["sort"] = self.sort if isinstance(self.sort, str) else ",".join(self.sort)
        if self.columns is not None:
            params["columns"] = self.columns if isinstance(self.columns, str) else ",".join(self.columns)
        if self.skip_received is not None:
            params["skip_received"] = str(self.skip_received).lower()
        if self.strict is not None:
            params["strict"] = str(self.strict).lower()

        for prefix in ("col", "min", "max"):
            filt = getattr(self, prefix)
            if filt:
                for key, val in filt.items():
                    params[f"{prefix}[{key}]"] = val

        for prefix in ("any", "has"):
            filt = getattr(self, prefix)
            if filt:
                for key, vals in filt.items():
                    params[f"{prefix}[{key}]"] = ",".join(vals)

        return params


def split_strip_i(v) -> list[str]:
    """Flatten comma-separated values into a list of stripped strings."""
    if not v:
        return []
    if isinstance(v, list):
        out: list[str] = []
        for item in v:
            out.extend(split_strip(str(item), ","))
        return out
    return split_strip(str(v), ",")

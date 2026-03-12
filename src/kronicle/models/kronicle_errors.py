from pydantic import BaseModel
from requests import Response


class KronicleError(Exception):
    """Base class for all Kronicle SDK errors."""


class KronicleConnectionError(KronicleError):
    """Raised when a connection to the Kronicle server fails."""


class KronicleResponseError(KronicleError):
    """Raised when the Kronicle server returns an unexpected response (invalid JSON, missing fields, etc.)."""


class KronicleOperationError(KronicleError):
    """Raised when Kronicle reports an error in its operation, e.g., failed insert, validation error, or op_status != 'success'."""

    def __init__(self, message: str, payload: dict | None = None):
        super().__init__(message)
        self.payload = payload


class KronicleHTTPErrorModel(BaseModel):
    status: int
    error: str
    message: str
    details: dict | None = None
    path: str
    method: str
    request_id: str | None = None


class KronicleHTTPError(KronicleError):
    def __init__(self, model: KronicleHTTPErrorModel):
        self.model = model
        super().__init__(str(self))

    @classmethod
    def from_response(cls, response: Response, path: str, method: str):
        res_json = response.json()
        model = KronicleHTTPErrorModel(**res_json)
        return cls(model)

    @classmethod
    def from_pydantic_response(cls, response: Response, path: str, method: str):
        res_json = response.json()
        model = KronicleHTTPErrorModel(
            status=response.status_code or 400,
            path=path,
            method=method,
            error="UnprocessableContent",
            message="Incorrect payload",
            details=res_json.get("detail"),
        )
        return cls(model)

    def __str__(self):
        m = self.model
        return (
            f"{m.status} {m.error}: {m.message} "
            + f"({m.details if m.details else None}) "
            + f"from request {m.method} {m.path}"
        )

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
    request_id: str


class KronicleHTTPError(KronicleError):
    def __init__(self, model: KronicleHTTPErrorModel):
        self.model = model
        super().__init__(str(self))

    @classmethod
    def from_response(cls, response: Response):
        model = KronicleHTTPErrorModel(**response.json())
        return cls(model)

    def __str__(self):
        m = self.model
        return f"{m.status} {m.error}: {m.message}\nfor request {m.method} {m.path}"

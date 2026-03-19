from typing import Any

from pydantic import BaseModel
from requests import Response


class KronicleError(Exception):
    """Base class for all Kronicle SDK errors."""


class KronicleConnectionError(KronicleError):
    """Raised when a connection to the Kronicle server fails."""


class KronicleResponseError(KronicleError):
    """Raised when the Kronicle server returns an unexpected response (invalid JSON, missing fields, etc.)."""


class KronicleOperationError(KronicleError):
    """
    Raised when Kronicle reports an error in its operation
    e.g., failed insert, validation error, or op_status != 'success'.
    """

    def __init__(self, message: str, payload: dict | None = None):
        super().__init__(message)
        self.payload = payload


class KronicleHTTPErrorModel(BaseModel):
    status: int
    error: str
    message: str
    details: Any = None
    method: str | None = None
    url: str | None = None
    request_id: str | None = None


class KronicleHTTPError(KronicleError):
    def __init__(self, model: KronicleHTTPErrorModel):
        self.model = model
        super().__init__(str(self))

    @classmethod
    def from_response(
        cls,
        response: Response,
        method: str | None = None,
        url: str | None = None,
    ):
        if not response or not response.content:
            raise KronicleResponseError("No response content received from Kronicle")

        if response.status_code and response.status_code == 422:
            return KronicleHTTPError.from_pydantic_response(
                response,
                method=response.request.method if response.request else method,
                url=response.request.url if response.request else url,
            )
        try:
            res = response.json()
            detail = res.get("detail")
            if detail:
                message = (detail.get("message"),)
                error = (detail.get("error"),)
                details = (detail.get("details"),)
                return cls(
                    KronicleHTTPErrorModel(
                        status=response.status_code or 400,
                        method=response.request.method if response.request else method,
                        url=response.request.url if response.request else url,
                        error=str(error),
                        message=str(message),
                        details=details,
                    )
                )
            else:
                return cls(
                    KronicleHTTPErrorModel(
                        status=response.status_code or 400,
                        method=response.request.method if response.request else method,
                        url=response.request.url if response.request else url,
                        error=str(res.reason),
                        message=str(res.reason),
                        details=res.reason,
                    )
                )
        except Exception:
            try:
                details = response.reason
                status = response.status_code or 400
                err = KronicleHTTPErrorModel(
                    status=response.status_code or 400,
                    url=response.request.url if response.request else url,
                    method=response.request.method if response.request else method,
                    error=f"Error {status}",
                    message=str(response.reason),
                    details=response.reason,
                )
                return cls(err)
            except Exception:
                response.raise_for_status()
                return cls(
                    KronicleHTTPErrorModel(
                        status=400,
                        method=method,
                        url=url,
                        error="No response",
                        message="No response received from the server",
                    )
                )

    @classmethod
    def from_pydantic_response(cls, response: Response, url: str | None = None, method: str | None = None):
        try:
            res_json = response.json()
            return cls(
                KronicleHTTPErrorModel(
                    status=response.status_code or 400,
                    url=response.request.url if response.request else url,
                    method=response.request.method if response.request else method,
                    error="UnprocessableContent",
                    message="Incorrect payload",
                    details=res_json.get("detail"),
                )
            )
        except Exception:
            response.raise_for_status()
            return cls(
                KronicleHTTPErrorModel(
                    status=response.status_code or 400,
                    url=response.request.url if response.request else url,
                    method=response.request.method if response.request else method,
                    error="UnprocessableContent",
                    message="Incorrect payload",
                    details=response.reason,
                )
            )

    def __str__(self):
        m = self.model
        return (
            f"{m.status} {m.error}: {m.message} "
            + f"({m.details if m.details else None}) "
            + f"from request {m.method} {m.url}"
        )

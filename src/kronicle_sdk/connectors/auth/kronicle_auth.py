# kronicle/connectors/kronicle_login.py
from json import loads
from time import sleep
from typing import Any, Callable

from requests import Response, post

from kronicle_sdk.conf.read_conf import Settings
from kronicle_sdk.connectors.abc_connector import KronicleAbstractConnector
from kronicle_sdk.models.iso_datetime import IsoDateTime
from kronicle_sdk.models.kronicle_errors import (
    KronicleConnectionError,
    KronicleHTTPError,
    KronicleResponseError,
)
from kronicle_sdk.utils.log import log_d, log_w
from kronicle_sdk.utils.str_utils import decode_b64url, get_type, slash_join


class KronicleUsrLogin(KronicleAbstractConnector):
    def __init__(self, url: str, usr: str, pwd: str) -> None:
        super().__init__(url)
        self.usr = usr
        self.pwd = pwd
        self._jwt: str | None = None
        self._exp: int | None = None

    @property
    def prefix(self) -> str:
        return "/auth/v1"

    @property
    def jwt(self) -> str:
        if self._jwt and self.is_jwt_valid():
            return self._jwt

        # log_d("get_jwt", f"login as '{self.usr}'...")
        res: Response = post(
            url=slash_join(self.url, "/auth/v1/login"),
            json={"login": self.usr, "password": self.pwd},
        )
        return self._renew_jwt_from_res(res.json())

    def _renew_jwt_from_res(self, res_json: dict) -> str:
        jwt = res_json.get("access_token")
        if jwt and isinstance(jwt, str):
            self._jwt = jwt
            self._exp = None
            log_d("get_jwt", f"logged in as '{self.usr}' on", self.url)
            return self._jwt
        else:
            raise KronicleResponseError("Not field 'access_token' fond in server response")

    @property
    def auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.jwt}"}

    @property
    def jwt_exp(self) -> int:
        if not self._jwt:
            return 0
        if self._exp is not None:
            return self._exp
        jwt_payload = loads(decode_b64url(self._jwt.split(".")[1]))
        exp = int(jwt_payload.get("exp"))
        self._exp = exp if exp is not None else 0
        return self._exp

    def is_jwt_valid(self) -> bool:
        if not self._jwt:
            return False
        now = IsoDateTime.now_timestamp()
        return now < self.jwt_exp

    def _request(
        self,
        method: Callable,
        route: str | None = None,
        body: Any | None = None,
        *,
        strict: bool = True,
        should_log: bool = True,
        **params,
    ):
        """
        Execute an HTTP request with retries and validated payload.

        Retry only on connection-level errors; do not retry on HTTP 4xx/5xx
        or malformed responses.

        Args:
            method: requests HTTP method (get, post, put, delete, patch)
            route: route path to append to base URL
            body: optional payload (dict or KroniclePayload)
            strict: validate the response as KroniclePayload(s)
            params: URL query parameters or other requests kwargs

        Raises:
            KronicleConnectionError: all retries exhausted
            KronicleHTTPError: HTTP 4xx/5xx response
            KronicleResponseError: response not JSON or invalid format
            TypeError: body type is invalid
        """
        here = f"{get_type(self)}.request"
        url = self._join(route)
        method_str = self.method_str(method)

        json_body = self._serialize_payload(body)
        headers = {"Authorization": f"Bearer {self.jwt}"}

        # Build kwargs without mutating user params
        request_kwargs = params.copy()
        if json_body is not None:
            request_kwargs["json"] = json_body

        last_exc = None
        for attempt in range(1, self._retries + 1):
            try:
                if should_log:
                    log_d(here, "Request", method_str, url)
                response: Response = method(url=url, headers=headers, **request_kwargs)
                if should_log:
                    log_d(here, "Response", response.json())

                if response.status_code and response.status_code == 422:
                    raise KronicleHTTPError.from_pydantic_response(response, path=url, method=method_str)
                if response.status_code and response.status_code >= 400:
                    raise KronicleHTTPError.from_response(response, path=url, method=method_str)

                return self._parse(response=response, strict=strict)

            except (KronicleResponseError, KronicleHTTPError) as exc:
                # Non-retriable: malformed response or HTTP error
                log_w(here, f"[attempt {attempt}] Non-retriable error", exc)
                raise exc
            except Exception as exc:
                # retriable: network error, timeout, etc.
                log_d(here, "type(exc)", type(exc))
                last_exc = exc
                log_w(here, f"[attempt {attempt}] retriable exception", exc)
                sleep(self._delay)

        raise KronicleConnectionError(f"Failed to connect to {url} after {self._retries} attempts") from last_exc

    def change_password(self, new_password: str):
        res = self.post(
            "/change_password",
            {
                "login": self.usr,
                "password": self.pwd,
                "new_password": new_password,
                "confirm_password": new_password,
            },
        )
        return self._renew_jwt_from_res(res)


if __name__ == "__main__":  # pragma: no cover
    tests = "login"
    co = Settings().connection
    log_d(tests, "login", co.usr, co.pwd)

    login = KronicleUsrLogin(co.url, co.usr, co.pwd)
    log_d(tests, "jwt", login.jwt)

    # log_d(tests, "new_jwt", login.change_password("Toto456789!"))

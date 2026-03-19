# kronicle/connectors/kronicle_login.py
from json import loads
from typing import Any, Callable

from requests import Response, post

from kronicle_sdk.conf.read_conf import Settings
from kronicle_sdk.connectors.abc_connector import KronicleAbstractConnector
from kronicle_sdk.models.iso_datetime import IsoDateTime
from kronicle_sdk.models.kronicle_errors import (
    KronicleResponseError,
)
from kronicle_sdk.utils.log import log_d, log_e
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
        here = "get_jwt"
        if self._jwt and self.is_jwt_valid():
            return self._jwt

        # log_d("get_jwt", f"login as '{self.usr}'...")
        login_url = slash_join(self.url, "/auth/v1/login")
        log_d(here, "login_url", login_url)
        res: Response = post(
            url=login_url,
            json={"login": self.usr, "password": self.pwd},
            timeout=5,
        )
        try:
            data = self._parse(res)
        except Exception:
            log_e(here, "Failed to get a JWT")
            raise
        if res.status_code and res.status_code > 399:
            log_e(here, "res", data)
        return self._renew_jwt_from_res(data)

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

        try:
            if should_log:
                log_d(here, "Request", method_str, url)
            response: Response = method(url=url, headers=headers, **request_kwargs)
            return self._parse(response=response, strict=strict)

        except Exception as exc:
            # retriable: network error, timeout, etc.
            log_e(here, "type(exc)", type(exc))
            raise

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
    co = Settings().connection_su
    if not co:
        raise RuntimeError("Not found: SU credentials")

    log_d(tests, "login", co.usr, co.pwd)
    login = KronicleUsrLogin(co.url, co.usr, co.pwd)
    log_d(tests, "jwt", login.jwt)

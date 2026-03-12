# kronicle/connectors/kronicle_login.py
from json import loads

from requests import Response, post

from kronicle.conf.read_conf import Settings
from kronicle.connectors.abc_connector import KronicleAbstractConnector
from kronicle.models.iso_datetime import IsoDateTime
from kronicle.models.kronicle_errors import KronicleConnectionError
from kronicle.utils.log import log_d
from kronicle.utils.str_utils import decode_b64url, slash_join


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
        data = res.json()
        jwt = data.get("access_token")
        if jwt and isinstance(jwt, str):
            self._jwt = jwt
            self._exp = None
            log_d("get_jwt", f"logged in as '{self.usr}' on", self.url)

            return self._jwt
        else:
            raise KronicleConnectionError(f"Could not log to the Kronicle server at {self.url}")

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


if __name__ == "__main__":  # pragma: no cover
    tests = "login"
    co = Settings().connection
    login = KronicleUsrLogin(co.url, co.usr, co.pwd)
    log_d(tests, "jwt", login.jwt)

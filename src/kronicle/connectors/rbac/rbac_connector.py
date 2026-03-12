from kronicle.conf.read_conf import Settings
from kronicle.connectors.auth.kronicle_login import KronicleUsrLogin
from kronicle.models.rbac.kronicle_user import KronicleUser
from kronicle.utils.log import log_d


class KronicleRbacConnector(KronicleUsrLogin):
    def __init__(self, url: str, usr: str, pwd: str) -> None:
        super().__init__(url, usr, pwd)

    @property
    def prefix(self) -> str:
        return "/rbac/v1"

    def get_all_users(self) -> list[KronicleUser]:
        list_users = self.get(route="/users")
        return [KronicleUser(**usr) for usr in list_users]

    def get_user_by(
        self,
        email: str | None = None,
        name: str | None = None,
        orcid: str | None = None,
    ) -> KronicleUser | None:
        if email:
            user = self.get(route=f"/users?email={email}")
        elif name:
            user = self.get(route=f"/users?name={name}")
        elif orcid:
            user = self.get(route=f"/users?orcid={orcid}")
        else:
            raise ValueError("One of the parameters should be given")
        return KronicleUser(**user) if user else None

    # def get_user(self, id):
    def create_user(self, user: KronicleUser) -> KronicleUser:
        usr = self.post(route="/users", body=user.to_json())
        return KronicleUser(**usr)

    # def get_user(self, id):
    def update_user(self, user: KronicleUser) -> KronicleUser:
        usr = self.put(route="/users", body=user.to_json())
        return KronicleUser(**usr)


if __name__ == "__main__":
    here = "abstract Kronicle connector"
    log_d(here)
    co = Settings().connection
    kronicle_rbac = KronicleRbacConnector(co.url, co.usr, co.pwd)
    usr_list = kronicle_rbac.get_all_users()
    [log_d(here, usr) for usr in usr_list]
    usr1 = usr_list[0]
    log_d(here, "usr1 obj", usr1)
    log_d(here, "usr1.email", usr1.email)

    log_d("get by email", kronicle_rbac.get_user_by(email=usr1.email))
    log_d("get by name", kronicle_rbac.get_user_by(name=usr1.name))
    log_d("get fake name", kronicle_rbac.get_user_by(name=f"{usr1.name}3"))

    usr2 = KronicleUser(
        email="dave@toto.fr",
        name="Dave2",
        orcid="1234-5678-9102",
        full_name="Dave Bond II",
        # password="Wonderful_Secrets_123403657",
    )
    kronicle_rbac.update_user(usr2)

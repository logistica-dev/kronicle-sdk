from kronicle_sdk.connectors.auth.kronicle_auth import KronicleUsrLogin
from kronicle_sdk.models.rbac.kronicle_user import KronicleUser


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
    def patch_user(self, user: KronicleUser) -> KronicleUser:
        usr = self.patch(route="/users", body=user.to_json())
        return KronicleUser(**usr)

    # def get_user(self, id):
    def delete_user(self, user: KronicleUser) -> KronicleUser:
        usr = self.delete(route="/users", body=user.to_json())
        return KronicleUser(**usr)

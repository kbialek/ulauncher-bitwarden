from requests import get, post


class BitwardenCliError(Exception):
    """ Contains error message returned by bitwarden-cli """

    def __init__(self, message):
        self.message = message


class BitwardenVaultLockedError(BitwardenCliError):

    def __init__(self, message):
        self.message = message


class BitwardenClient:
    """ Wrapper around bitwarden-cli """

    def __init__(self):
        self.url = "http://localhost:8087"
        self.status = {}
        self.folders = {}
        try:
            self.status = get(
                url="{}/status".format(self.url),
            )
            self.status.raise_for_status()
        except Exception as err:
            raise BitwardenCliError(str(err)) from err

    def configure(self, url):
        """
        """
        self.url = url or self.url

    def is_unlocked(self):
        res = get(
            url="{}/status".format(self.url),
        ).json()
        if res.get("data", {}).get("template", {}).get("status", "") in ["unlocked"]:
            return True
        return False

    def unlock(self, pp):
        try:
            res = post(
                url="{}/unlock".format(self.url),
                json={"password": pp},
            ).json()
            self.list_folders()
            return res.get("success")
        except Exception as err:
            raise BitwardenCliError(str(err)) from err

    def lock(self):
        if not self.is_unlocked:
            return True
        try:
            res = post(
                url="{}/lock".format(self.url),
            ).json()
            return res.get("success")
        except Exception as err:
            raise BitwardenCliError(str(err)) from err

    def sync(self):
        try:
            res = post(
                url="{}/sync".format(self.url),
            ).json()
            return res.get("success")
        except Exception as err:
            raise BitwardenCliError(str(err)) from err

    def list_folders(self):
        self.folders = {}
        try:
            res = get(
                url="{}/list/object/folders".format(self.url),
            ).json()
            if not res.get("success"):
                return False
            self.folders = dict()
            for item in res.get("data", {}).get("data", []):
                self.folders[item["id"]] = item["name"]
            return True
        except Exception as err:
            raise BitwardenCliError(str(err)) from err

    def get_folder(self, folder_id):
        if folder_id in self.folders:
            return self.folders[folder_id]
        else:
            return ""

    def search(self, query):
        if len(query) < 2:
            return []
        try:
            res = get(
                url="{}/list/object/items".format(self.url),
                params={"search": query},
            ).json()
            if not res.get("success"):
                raise BitwardenCliError(res.get("message"))
            return res.get("data", {}).get("data", [])
        except Exception as err:
            raise BitwardenCliError(str(err)) from err

    def get_entry_details(self, entry):
        attrs = {}
        try:
            res = get(
                url="{}/object/item/{}".format(self.url, entry),
            ).json()
            if not res.get("success"):
                raise BitwardenCliError(res.get("message"))
            login = res.get("data", {}).get("login")
            if "fields" in res.get("data", {}):
                attrs["fields"] = res.get("data", {}).get("fields")
            attrs["username"] = login.get("username")
            attrs["password"] = login.get("password")
            if "uris" in login:
                uris = login.get("uris")
                attrs["uri"] = uris[0]["uri"] if uris else ""
            if login.get("totp"):
                res = get(
                    url="{}/object/totp/{}".format(self.url, entry),
                ).json()
                attrs["totp"] = res.get("data", {}).get("data", "")
            return attrs
        except Exception as err:
            raise BitwardenCliError(str(err)) from err

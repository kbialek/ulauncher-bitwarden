import subprocess
from datetime import datetime, timedelta
import json
from json import JSONDecodeError


class BitwardenCliNotFoundError(Exception):
    pass


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
        self.cli = "bw"
        self.init_done = False
        self.path = None
        self.path_checked = False
        self.server = None
        self.email = None
        self.session = None
        self.folders = None
        self.mfa_enabled = None
        self.passphrase_expires_at = None
        self.inactivity_lock_timeout = 0
        self.session_store_cmd = ""

    def initialize(self, server, email, mfa_enabled, inactivity_lock_timeout, session_store_cmd):
        """
        Check that
        - we can call the CLI
        Don't call more than once.
        """
        self.server = server
        self.email = email
        self.mfa_enabled = mfa_enabled
        self.inactivity_lock_timeout = inactivity_lock_timeout
        self.session_store_cmd = session_store_cmd
        if not self.init_done:
            self.configure_server()
            if self.can_execute_cli():
                self.init_done = True
            else:
                raise BitwardenCliNotFoundError()

        if self.inactivity_lock_timeout and self.passphrase_expires_at is not None:
            if datetime.now() > self.passphrase_expires_at:
                self.lock()

    def change_server_url(self, new_server_url):
        """
        Change the path to the database file and lock the database.
        """
        self.logout()
        self.server = new_server_url
        self.passphrase_expires_at = None
        self.configure_server()

    def change_email(self, new_email):
        """
        Change the path to the database file and lock the database.
        """
        self.logout()
        self.email = new_email
        self.passphrase_expires_at = None

    def change_inactivity_lock_timeout(self, secs):
        """
        Change the inactivity lock timeout and immediately lock the database.
        """
        self.inactivity_lock_timeout = secs
        self.passphrase_expires_at = None

    def change_session_store_cmd(self, cmd):
        """
        Change the inactivity lock timeout and immediately lock the database.
        """
        self.session_store_cmd = cmd

    def configure_server(self):
        self.run_cli_session("config", "server", self.server)

    def need_login(self):
        try:
            (err, out) = self.run_cli_session("login", "--check")
            return self.handle_unlock_result(err, out)
        except BitwardenVaultLockedError:
            return True

    def need_mfa(self):
        return self.mfa_enabled

    def need_unlock(self):
        if not self.has_session():
            return True
        (err, out) = self.run_cli_session("unlock", "--check")
        return self.handle_unlock_result(err, out)

    def has_session(self):
        return self.session is not None

    @staticmethod
    def handle_unlock_result(err, out):
        if out:
            try:
                result = out["success"] is False
                return result
            except JSONDecodeError:
                raise BitwardenCliError(err)
        else:
            return False

    def verify_and_set_passphrase(self, pp, mfa):
        success = False
        if self.need_login():
            success = self.login(pp, mfa)
        elif self.need_unlock():
            success = self.unlock(pp)
        if success:
            self.run_cli_store_session()
            self.list_folders()
        return success

    def login(self, pp, mfa):
        args = ["login", self.email, "--raw"]
        if self.mfa_enabled and mfa:
            args.append("--code")
            args.append(mfa)
        (err, out) = self.run_cli_pp(pp, *args)
        if out:
            self.session = out
            return True
        else:
            self.session = None
            return False

    def logout(self):
        self.session = None
        (err, out) = self.run_cli_session("logout")
        if err:
            raise BitwardenCliError(err)

    def unlock(self, pp):
        (err, out) = self.run_cli_pp(pp, "unlock", "--raw")
        if out:
            self.session = out
            return True
        else:
            self.session = None
            return False

    def lock(self):
        self.session = None
        (err, out) = self.run_cli_session("lock")
        if err:
            raise BitwardenCliError(err)
        else:
            return True

    def sync(self):
        (err, out) = self.run_cli_session("sync")
        if err:
            raise BitwardenCliError(err)
        else:
            self.list_folders()
            return True

    def list_folders(self):
        (err, out) = self.run_cli_session("list", "folders")
        if err:
            self.folders = None
            return False
        else:
            self.folders = dict()
            for item in out["data"]["data"]:
                self.folders[item["id"]] = item["name"]
            return True

    def get_folder(self, folder_id):
        if folder_id in self.folders:
            return self.folders[folder_id]
        else:
            return ""

    def search(self, query):
        if len(query) < 2:
            return []

        (err, out) = self.run_cli_session("list", "items", "--search", query)
        if err:
            raise BitwardenCliError(err)
        else:
            return out["data"]["data"]

    def get_entry_details(self, entry):
        attrs = dict()

        (err, out) = self.run_cli_session("get", "item", entry)
        if err:
            raise BitwardenCliError(err)
        else:
            data = out["data"]
            login = data["login"]
            if "fields" in data:
                attrs["fields"] = data["fields"]

            attrs["username"] = login["username"]
            attrs["password"] = login["password"]
            if "uris" in login:
                uris = login["uris"]
                attrs["uri"] = uris[0]["uri"] if uris else ""

            if "totp" in login and login["totp"]:
                (err, out) = self.run_cli_session("get", "totp", entry)
                attrs["totp"] = out["data"]["data"]
        return attrs

    def can_execute_cli(self):
        try:
            subprocess.run([self.cli], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

    def get_bw_version(self):
        try:
            cp = subprocess.run(
                [self.cli, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise BitwardenCliNotFoundError()

        out = cp.stdout.decode("utf-8")
        return str(out).strip()

    def run_cli_session(self, *args):
        session_args = ["--session", self.session] if self.session else []
        try:
            cp = subprocess.run(
                [self.cli, *args, "--response", *session_args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise BitwardenCliNotFoundError()

        if self.inactivity_lock_timeout:
            self.passphrase_expires_at = datetime.now() + timedelta(
                seconds=self.inactivity_lock_timeout
            )

        err = cp.stderr.decode("utf-8")
        out = cp.stdout.decode("utf-8")

        err_json = None
        out_json = None

        if out:
            out_json = json.loads(out)
            if not out_json["success"] and out_json["message"] == "You are not logged in.":
                raise BitwardenVaultLockedError(out_json["message"])

        return err_json, out_json

    def run_cli_pp(self, passphrase, *args):
        try:
            cp = subprocess.run(
                [self.cli, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                input=bytes(passphrase, "utf-8"),
            )
        except FileNotFoundError:
            raise BitwardenCliNotFoundError()

        if self.inactivity_lock_timeout:
            self.passphrase_expires_at = datetime.now() + timedelta(
                seconds=self.inactivity_lock_timeout
            )

        return cp.stderr.decode("utf-8"), cp.stdout.decode("utf-8")

    def run_cli_store_session(self):
        if self.session_store_cmd == '':
            return
        try:
            cp = subprocess.run(
                [self.session_store_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                input=bytes(self.session, "utf-8"),
            )
        except FileNotFoundError:
            raise BitwardenCliNotFoundError()
        except Exception as e:
            raise BitwardenCliError(e)

import subprocess
import os
from datetime import datetime, timedelta
import json
from json import JSONDecodeError


class KeepassxcCliNotFoundError(Exception):
    pass


class KeepassxcFileNotFoundError(Exception):
    pass


class KeepassxcCliError(Exception):
    """ Contains error message returned by keepassxc-cli """

    def __init__(self, message):
        self.message = message

class KeepassxcDatabase:
    """ Wrapper around keepassxc-cli """

    def __init__(self):
        self.cli = "bw"
        self.cli_checked = False
        self.path = None
        self.path_checked = False
        self.server = None
        self.email = None
        self.session = None
        self.folders = None
        self.mfa_enabled = None
        self.passphrase_expires_at = None
        self.inactivity_lock_timeout = 0

    def initialize(self, server, email, mfa_enabled, inactivity_lock_timeout):
        """
        Check that
        - we can call the CLI
        Don't call more than once.
        """
        self.server = server
        self.email = email
        self.mfa_enabled = mfa_enabled
        self.inactivity_lock_timeout = inactivity_lock_timeout
        if not self.cli_checked:
            if self.can_execute_cli():
                self.cli_checked = True
            else:
                raise KeepassxcCliNotFoundError()

    def change_server_url(self, new_server_url):
        """
        Change the path to the database file and lock the database.
        """
        self.logout()
        self.server = new_server_url
        self.passphrase_expires_at = None

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

    def need_login(self):
        (err, out) = self.run_cli("login", "--check", "--response")
        if err:
            try:
                resp = json.loads(err)
                result = resp["success"] is False
                if result and self.inactivity_lock_timeout:
                    if datetime.now() > self.passphrase_expires_at:
                        self.session = None
                return result
            except JSONDecodeError:
                raise KeepassxcCliError(err)
        else:
            return False

    def need_mfa(self):
        return self.mfa_enabled

    def need_unlock(self):
        if self.session is None:
            return True
        (err, out) = self.run_cli("unlock", "--check", "--response", "--session", self.session)
        if err:
            try:
                resp = json.loads(err)
                return resp["success"] is False
            except JSONDecodeError:
                raise KeepassxcCliError(err)
        else:
            return False

    def verify_and_set_passphrase(self, pp, mfa):
        if self.unlock(pp) or self.login(pp, mfa):
            self.list_folders()
            return True
        else:
            return False

    def login(self, pp, mfa):
        args = ["login", self.email, pp, "--raw"]
        if self.mfa_enabled and mfa:
            args.append("--code")
            args.append(mfa)
        (err, out) = self.run_cli(*args)
        if err:
            self.session = None
            return False
        else:
            self.session = out
            return True

    def logout(self):
        self.session = None
        (err, out) = self.run_cli("logout")
        if err:
            raise KeepassxcCliError(err)

    def unlock(self, pp):
        (err, out) = self.run_cli("unlock", pp, "--raw")
        if err:
            self.session = None
            return False
        else:
            self.session = out
            return True

    def list_folders(self):
        (err, out) = self.run_cli("list", "folders", "--session", self.session)
        if err:
            self.folders = None
            return False
        else:
            self.folders = dict()
            for item in json.loads(out):
                self.folders[item["id"]] = item["name"]
            return True

    def get_folder(self, folder_id):
        return self.folders[folder_id]

    def search(self, query):
        if len(query) < 2:
            return []
        (err, out) = self.run_cli("list", "items", "--search", query, "--session", self.session)
        if err:
            if "No results for that" in err:
                return []
            else:
                raise KeepassxcCliError(err)
        else:
            return json.loads(out)

    def get_entry_details(self, entry):
        attrs = dict()
        for attr in ["username", "password", "totp", "uri"]:
            (err, out) = self.run_cli(
                "get", attr, entry, "--session", self.session, "--response"
            )
            if err:
                try:
                    json.loads(err)
                except JSONDecodeError:
                    raise KeepassxcCliError(err)
            else:
                resp = json.loads(out)
                attrs[attr] = resp["data"]["data"]
        return attrs

    def can_execute_cli(self):
        try:
            subprocess.run([self.cli], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

    def run_cli(self, *args):
        try:
            cp = subprocess.run(
                [self.cli, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # input=bytes(self.passphrase, "utf-8"),
            )
        except FileNotFoundError:
            raise KeepassxcCliNotFoundError()

        if self.inactivity_lock_timeout:
            self.passphrase_expires_at = datetime.now() + timedelta(
                seconds=self.inactivity_lock_timeout
            )

        return cp.stderr.decode("utf-8"), cp.stdout.decode("utf-8")

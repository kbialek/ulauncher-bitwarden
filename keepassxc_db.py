import subprocess
import os


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
        self.cli = "keepassxc-cli"
        self.cli_checked = False
        self.path = None
        self.path_checked = False
        self.passphrase = None

    def initialize(self, path):
        if not self.cli_checked:
            if self.can_execute_cli():
                self.cli_checked = True
            else:
                raise KeepassxcCliNotFoundError()

        if path != self.path:
            self.path = os.path.expanduser(path)
            self.path_checked = False
            self.passphrase = None

        if not self.path_checked:
            if os.path.exists(self.path):
                self.path_checked = True
            else:
                raise KeepassxcFileNotFoundError()

    def need_passphrase(self):
        return self.passphrase is None

    def validate_and_set_passphrase(self, pp):
        self.passphrase = pp
        (err, out) = self.run_cli("ls", "-q", self.path)
        if err:
            self.passphrase = None
            return False
        else:
            return True

    def search(self, query):
        (err, out) = self.run_cli("locate", "-q", self.path, query)
        if err:
            if "No results for that" in err:
                return []
            else:
                raise KeepassxcCliError(err)
        else:
            return out.splitlines()

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
                input=bytes(self.passphrase, "utf-8"),
            )
        except FileNotFoundError:
            raise KeepassxcCliNotFoundError()
        return (cp.stderr.decode("utf-8"), cp.stdout.decode("utf-8"))

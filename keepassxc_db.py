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

def pretty_entry_fmt(s):
    return s[1:]

def cli_entry_fmt(s):
    return "/" + s

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

    def verify_and_set_passphrase(self, pp):
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
            # Entry names in keepassxc-cli start with a "/" (because kdbx files have a tree structure with "folders" etc)
            # For aesthetic purposes, we are removing the leading "/" here by blindly cutting off the first char
            # but will add it back any time we need to pass an entry name to the CLI as an argument
            return [pretty_entry_fmt(l) for l in out.splitlines()]

    def get_entry_details(self, entry):
        attrs = dict()
        for attr in ["UserName", "Password", "URL", "Notes"]:
            (err, out) = self.run_cli("show", "-q", "-a", attr, self.path, cli_entry_fmt(entry))
            if err:
                raise KeepassxcCliError(err)
            else:
                attrs[attr] = out.strip("\n")
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
                input=bytes(self.passphrase, "utf-8"),
            )
        except FileNotFoundError:
            raise KeepassxcCliNotFoundError()
        return (cp.stderr.decode("utf-8"), cp.stdout.decode("utf-8"))

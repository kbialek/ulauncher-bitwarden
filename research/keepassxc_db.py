import subprocess


class KeepassxcNotInstalledException(Exception):
    pass


class KeepassxcDatabaseFileNotFound(Exception):
    pass


class KeepassxcCliException(Exception):
    """ Contains error message returned by keepassxc-cli """

    def __init__(self, message):
        self.message = message


class KeepassxcDatabase:
    """ Wrapper around keepassxc-cli """

    def __init__(self, path, passphrase):
        self.path = path
        self.passphrase = passphrase

    # TODO check passphrase method?

    def run_cli(self, cmd, *args):
        # TODO check db file and raise if not
        try:
            cp = subprocess.run(
                ["keepassxc-cli", cmd, "-q", self.path, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                input=bytes(self.passphrase, "utf-8"),
            )
        except FileNotFoundError:
            raise KeepassxcNotInstalledException()
        if cp.stderr:
            raise KeepassxcCliException(cp.stderr.decode("utf-8"))
        return cp.stdout.decode("utf-8")


db = KeepassxcDatabase("/home/peter/SynologyDrive/passwords/Passwords.kdbx", "asdf")
print(db.run_cli("locate", "amex"))

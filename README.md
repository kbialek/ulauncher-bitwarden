# ulauncher-keepassxc

A [Ulauncher](https://ulauncher.io/) extension to search your [KeePassXC](https://keepassxc.org/) password manager database and copy passwords to the clipboard.

## Features

- Quickly search through the database entries by name, and copy passwords/usernames/URLs to the clipboard
- Work with any file (.kdbx etc) that can be accessed by the KeePassXC itself via the `keepassxc-cli` command line tool
- Support files locked with a passphrase. The extension asks for the passphrase and stores it in memory for a configurable amount of time
- Doesn't require the KeePassXC app to be running

## Requirements

- Install a recent version of [KeePassXC](https://keepassxc.org/download/)
- Make sure you can execute `keepassxc-cli` in a terminal

## Installation

Open Ulauncher preferences window -> Extensions -> "Add extension" and paste the following url:

```
https://github.com/pbkhrv/ulauncher-keepassxc
```

## Configuration

- `Password database location`: path to the password database file that you want to access through Ulauncher. *This is the only preference that you need to set before you can use the extension.*

- `Inactivity lock timeout`: forces you to re-enter the passphrase after you haven't used the extension for a while. By default it's set to 600 seconds (10 minutes). If you'd rather not re-enter it, you can set the value to 0, but that's probably not a great idea. NOTE: The cached passphrase is only stored in memory, so you'll need to re-enter it if you reboot your computer or restart Ulauncher.

## Usage

Open Ulauncher and type in "kp " to start the extension. If your password database is locked with a passphrase, it'll ask you to enter it:

![Unlock Database](images/screenshots/unlock-database.png)

Once unlocked, search the database for Github logins:

![Search](images/screenshots/search1.png)

Look at the `Github work` entry:

![Entry details](images/screenshots/details1.png)

## Inspiration and thanks

I loved Alfred on MacOS, and now I love Ulauncher on Linux. The Python API is simple yet powerful.

Thanks to [pass-ulauncher](https://github.com/yannishuber/pass-ulauncher) for the overall structure and for teaching me a few things about the API. I aaaalmost switched away from KeePassXC to [pass: the standard unix password manager](https://www.passwordstore.org/) because of it.

[The Noun Project](https://thenounproject.com/) for the icons - there's nothing else quite like it.

Finally, thanks to [KeePassXC](https://keepassxc.org/) on Linux and [KyPass](https://www.kyuran.be/software/kypass/) on iOS.
# ulauncher-bitwarden

A [Ulauncher](https://ulauncher.io/) extension to search your [Bitwarden](https://bitwarden.com/) vault and copy passwords to the clipboard.

## Features

- Leverage [`bw`](https://bitwarden.com/help/cli/) in [RESTful API](https://bitwarden.com/help/cli/#serve) mode (much faster!)
- Quickly search through the database entries by name, and copy passwords/usernames/URLs/TOTPs to the clipboard
- Works also with self hosted Bitwarden servers.

## Requirements

- Install a recent version of [Bitwarden CLI](https://github.com/bitwarden/clients/tree/master/apps/cli)
- Install python requests module (e.g. `sudo apt-get install python3-requests`)

## Installation

### `bw serve` systemd service

- Make sure `bw` works in a shell session (e.g. configuring server, e-mail, ...)
- Create a user systemd directory: `mkdir -p ~/.config/systemd/user`
- Create a user service in `~/.config/systemd/user/bw.service` with the following content
  - Your `ExecStart` may vary (e.g. `%h/bin/bw serve` if you have it in your home directory)

```
[Unit]
Description=Bitwarden CLI RESTful API
After=network.target

[Service]
ExecStart=/usr/bin/bw serve
Restart=on-failure

[Install]
WantedBy=default.target
```

### Ulauncher

- Open Ulauncher preferences window -> Extensions -> "Add extension" and paste the following url:

```
https://github.com/morph027/ulauncher-bitwarden
```

## Configuration

- `Bitwarden CLI serve url`

## Usage

Open Ulauncher and type in "bw " to start the extension. If your password database is locked with a passphrase, it'll ask you to enter it:

![Unlock Database](images/screenshots/unlock-database.png)

Once unlocked, search the database for "mail" logins:

![Search](images/screenshots/search1.png)

Look at the `GMail` entry:

![Entry details](images/screenshots/details1.png)

## Inspiration and thanks

This is a fork of well crafted [ulauncher-bitwarden](https://github.com/kbialek/ulauncher-bitwarden) extension. Thank you @kbialek! 

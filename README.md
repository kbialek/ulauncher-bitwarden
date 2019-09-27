ulauncher-keepassxc
===================

Features:
=========
- prompt user to enter the database passphrase and cache it for a certain amount of time
- search for and copy passwords from a KeePassXC database (.kdbx file)

The Plan:
=========
- on any invocation
	- check if need passphrase to unlock db
	- if unnecessary or have it cached, proceed
	- if dont have it, show "Enter passphrase" as the only item
		- use GTK to pop up an entry dialog, verify and cache the input (?)
- search: use "keepassxc-cli locate" to search for entries matching the query
- copy: when user selects an entry, use the cli "clip" command to copy password to clipboard

App states:
===========

db file    | passphrase | cli       | what to do
-----------|------------|-----------|-----------------------
-          | -          | not found | warn on every invocation
not found  | -          | -         | warn on every invocation
found      | none       | yes       | ask to enter, every time
found      | invalid    | yes       | ask to re-enter, every time
found      | dont need  | yes       | ok


Log:
====
sep 25
- woohoo! ulauncher extension that asks for a passphrase! it works!
- making a GTK password entry window
	- it works!

TODO:
=====
- search: feed passphrase into cli subprocess
- use "locate anything-at-all" command to check if we can open db file, before asking for passphrase. do this on first run and cache result for later.
- center the passphrase window
- size the passphrase window more better
- show notification when correct passphrase is entered

DONE:
=====
- simple GTK passphrase entry window

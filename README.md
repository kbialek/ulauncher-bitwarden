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
sep 27
- woohoo x2! pretty good code structure, got the passphrase flow working-ish
- next big step: SHOW REAL DB SEARCH RESULTS!

sep 25
- woohoo! ulauncher extension that asks for a passphrase! it works!
- making a GTK password entry window
	- it works!

TODO MVP:
=========
- move EntryWindow gtk code into separate file
- center the passphrase window
- size the passphrase window more better
- show notification when correct passphrase is entered
- show notification when incorrect passphrase is entered
- show notification when something is copied to clipboard
- remove the "/" prefix in entry names
- make real icons

TODO MVP+:
==========
- ?show passphrase window again with err message if wrong passphrase entered
- if user activates entry but doesnt do anything then presses backspace, reset userQuery to previous search term
- implement lock timeout: erase passphrase after X seconds (set in preferences)
- fuzzy search!
- handle "preferences set" event or whaterver
- support key file
- support yubikey
- find a graceful way to display notes - would love some preview window from which i can copy text, good for CCs etc
- show username(?) in description for search result items
- paginate results: "show more" pagination when too many results
- show "recently activated entries" if no search params entered (instead of empty list)
- if cli not accessible, open page with keepassxc-cli documentation

DONE:
=====
- simple GTK passphrase entry window
- search: feed passphrase into cli subprocess
- use "locate anything-at-all" command to check if we can open db file, before asking for passphrase. do this on first run and cache result for later.
- show "enter more words" if result list exceeds "max items"
- when entry is activated, show following items:
	- every key (except for password) - if selected, copy that to clipboard
	- "copy password to clipboard", without showing it on screen

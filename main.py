import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.ActionList import ActionList
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from keepassxc_db import (
    KeepassxcDatabase,
    KeepassxcCliNotFoundError,
    KeepassxcFileNotFoundError,
    KeepassxcCliError,
)

UNLOCK_ICON = "images/icon.svg"
ERROR_ICON = "images/icon.svg"
ITEM_ICON = "images/icon.svg"

KEEPASSXC_CLI_NOT_FOUND_ITEM = ExtensionResultItem(
    icon=ERROR_ICON,
    name="Cannot find or execute keepassxc-cli",
    description="Please make sure keepassxc-cli is installed and accessible",
    on_enter=DoNothingAction(),
)

KEEPASSXC_DB_NOT_FOUND_ITEM = ExtensionResultItem(
    icon=ERROR_ICON,
    name="Cannot find or access the database file",
    description="Check the password database file path in extension preferences",
    on_enter=DoNothingAction(),
)

NEED_PASSPHRASE_ITEM = ExtensionResultItem(
    icon=UNLOCK_ICON,
    name="Unlock KeePassXC database",
    description="Enter passphrase to unlock the KeePassXC database",
    on_enter=ExtensionCustomAction({"action": "need_passphrase"}),
)

WRONG_PASSPHRASE_ITEM = ExtensionResultItem(
    icon=UNLOCK_ICON,
    name="Wrong passphrase, please try again",
    description="Enter passphrase to unlock the KeePassXC database",
    on_enter=ExtensionCustomAction({"action": "need_passphrase"}),
)

ENTER_QUERY_ITEM = ExtensionResultItem(
    icon=ITEM_ICON,
    name="Enter search terms...",
    description="Please start typing the query to see results",
    on_enter=DoNothingAction()
)


def keepassxc_cli_error_item(message):
    return ExtensionResultItem(
        icon=ERROR_ICON,
        name="Error while calling keepassxc-cli",
        description=message,
        on_enter=DoNothingAction(),
    )


class EntryWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Enter passphrase")
        self.set_size_request(200, 100)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        self.passphrase = ""
        self.entry = Gtk.Entry()
        self.entry.set_text("")
        self.entry.set_editable(True)
        self.entry.set_visibility(False)
        self.entry.connect("activate", self.enter_pressed)
        self.entry.connect("key-press-event", self.key_pressed)
        vbox.pack_start(self.entry, True, True, 0)

    def close_window(self):
        self.destroy()
        Gtk.main_quit()

    def enter_pressed(self, entry):
        self.passphrase = entry.get_text()
        self.close_window()

    def key_pressed(self, widget, event):
        if event.hardware_keycode == 9:
            self.passphrase = ""
            self.close_window()

    def read_passphrase(self):
        self.connect("destroy", Gtk.main_quit)
        self.show_all()
        Gtk.main()
        return self.passphrase


class KeepassxcExtension(Extension):
    """ Extension class, coordinates everything """

    def __init__(self):
        super(KeepassxcExtension, self).__init__()
        self.keepassxc_db = KeepassxcDatabase()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener(self.keepassxc_db))
        self.subscribe(ItemEnterEvent, ItemEnterEventListener(self.keepassxc_db))

    def get_db_path(self):
        return self.preferences["database-path"]

    def get_max_result_items(self):
        return self.preferences["max-results"]


class KeywordQueryEventListener(EventListener):
    """ KeywordQueryEventListener class used to manage user input """

    def __init__(self, keepassxc_db):
        self.keepassxc_db = keepassxc_db

    def on_event(self, event, extension):
        try:
            self.keepassxc_db.initialize(extension.get_db_path())

            if self.keepassxc_db.need_passphrase():
                return RenderResultListAction([NEED_PASSPHRASE_ITEM])
            else:
                return self.process_keyword_query(event, extension)
        except KeepassxcCliNotFoundError:
            return RenderResultListAction([KEEPASSXC_CLI_NOT_FOUND_ITEM])
        except KeepassxcFileNotFoundError:
            return RenderResultListAction([KEEPASSXC_DB_NOT_FOUND_ITEM])
        except KeepassxcCliError as e:
            return RenderResultListAction([keepassxc_cli_error_item(e.message)])

    def render_search_results(self, keyword, entries, extension):
        max_items = int(extension.get_max_result_items())
        results = []
        for e in entries[:max_items]:
            action = ActionList(
                [
                    SetUserQueryAction("{} {}".format(keyword, e)),
                    ExtensionCustomAction({"action": "activate_entry", "entry": e}),
                ]
            )
            results.append(
                ExtensionSmallResultItem(icon=ITEM_ICON, name=e, on_enter=action)
            )
        return RenderResultListAction(results)

    def process_keyword_query(self, event, extension):
        query_keyword = event.get_keyword()
        query_args = event.get_argument()
        if not query_args:
            return RenderResultListAction([ENTER_QUERY_ITEM])
        else:
            entries = self.keepassxc_db.search(query_args)
            return self.render_search_results(query_keyword, entries, extension)


class ItemEnterEventListener(EventListener):
    """ KeywordQueryEventListener class used to manage user input """

    def __init__(self, keepassxc_db):
        self.keepassxc_db = keepassxc_db

    def on_event(self, event, extension):
        try:
            data = event.get_data()
            action = data.get("action", None)
            if action == "need_passphrase":
                return self.read_verify_passphrase(extension)
            elif action == "activate_entry":
                return self.activate_entry(data.get("entry"))
        except KeepassxcCliNotFoundError:
            return RenderResultListAction([KEEPASSXC_CLI_NOT_FOUND_ITEM])
        except KeepassxcFileNotFoundError:
            return RenderResultListAction([KEEPASSXC_DB_NOT_FOUND_ITEM])
        except KeepassxcCliError as e:
            return RenderResultListAction([keepassxc_cli_error_item(e.message)])

    def read_verify_passphrase(self, extension):
        win = EntryWindow()
        pp = win.read_passphrase()
        if not pp is None:
            if self.keepassxc_db.validate_and_set_passphrase(pp):
                # TODO notify of success
                pass
            else:
                # TODO notify of failure
                pass

    def activate_entry(self, entry):
        # TODO display relevant items
        pass


if __name__ == "__main__":
    KeepassxcExtension().run()

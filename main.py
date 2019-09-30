import gi

gi.require_version("Notify", "0.7")
from gi.repository import Notify
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
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from keepassxc_db import (
    KeepassxcDatabase,
    KeepassxcCliNotFoundError,
    KeepassxcFileNotFoundError,
    KeepassxcCliError,
)
from gtk_passphrase_entry import GtkPassphraseEntryWindow

UNLOCK_ICON = "images/icon.svg"
ERROR_ICON = "images/icon.svg"
ITEM_ICON = "images/icon.svg"
CLIP_ICON = "images/icon.svg"
EMPTY_ICON = "images/icon.svg"

KEEPASSXC_CLI_NOT_FOUND_ITEM = ExtensionResultItem(
    icon=ERROR_ICON,
    name="Cannot find or execute keepassxc-cli",
    description="Please make sure keepassxc-cli is installed and accessible",
    on_enter=DoNothingAction(),
)

KEEPASSXC_DB_NOT_FOUND_ITEM = ExtensionResultItem(
    icon=ERROR_ICON,
    name="Cannot find the database file",
    description="Check the password database file path in extension preferences",
    on_enter=DoNothingAction(),
)

NEED_PASSPHRASE_ITEM = ExtensionResultItem(
    icon=UNLOCK_ICON,
    name="Unlock KeePassXC database",
    description="Enter passphrase to unlock the KeePassXC database",
    on_enter=ExtensionCustomAction({"action": "read_passphrase"}),
)

WRONG_PASSPHRASE_ITEM = ExtensionResultItem(
    icon=UNLOCK_ICON,
    name="Wrong passphrase, please try again",
    description="Enter passphrase to unlock the KeePassXC database",
    on_enter=ExtensionCustomAction({"action": "read_passphrase"}),
)

ENTER_QUERY_ITEM = ExtensionResultItem(
    icon=ITEM_ICON,
    name="Enter search terms...",
    description="Please start typing to see results",
    on_enter=DoNothingAction(),
)

NO_SEARCH_RESULTS_ITEM = ExtensionSmallResultItem(
    icon=ITEM_ICON, name="No matching entries found...", on_enter=DoNothingAction()
)


def more_results_available_item(cnt):
    return ExtensionSmallResultItem(
        icon=EMPTY_ICON,
        name="...{} more results available, please refine the search query...".format(
            cnt
        ),
        on_enter=DoNothingAction(),
    )


def keepassxc_cli_error_item(message):
    return ExtensionResultItem(
        icon=ERROR_ICON,
        name="Error while calling keepassxc CLI",
        description=message,
        on_enter=DoNothingAction(),
    )


class KeepassxcExtension(Extension):
    """ Extension class, coordinates everything """

    def __init__(self):
        super(KeepassxcExtension, self).__init__()
        self.keepassxc_db = KeepassxcDatabase()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener(self.keepassxc_db))
        self.subscribe(ItemEnterEvent, ItemEnterEventListener(self.keepassxc_db))
        self.active_entry = None

    def get_db_path(self):
        return self.preferences["database-path"]

    def get_max_result_items(self):
        return self.preferences["max-results"]

    def set_active_entry(self, keyword, entry):
        self.active_entry = (keyword, entry)

    def check_and_reset_active_entry(self, keyword, entry):
        r = self.active_entry == (keyword, entry)
        self.active_entry = None
        return r

    def reset_active_entry(self):
        self.active_entry = None


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
        items = []
        if not entries:
            items.append(NO_SEARCH_RESULTS_ITEM)
        else:
            for e in entries[:max_items]:
                action = ExtensionCustomAction(
                    {"action": "activate_entry", "entry": e, "keyword": keyword},
                    keep_app_open=True,
                )
                items.append(
                    ExtensionSmallResultItem(icon=ITEM_ICON, name=e, on_enter=action)
                )
            if len(entries) > max_items:
                items.append(more_results_available_item(len(entries) - max_items))
        return RenderResultListAction(items)

    def process_keyword_query(self, event, extension):
        query_keyword = event.get_keyword()
        query_args = event.get_argument()
        if not query_args:
            return RenderResultListAction([ENTER_QUERY_ITEM])
        else:
            if extension.check_and_reset_active_entry(query_keyword, query_args):
                return self.show_active_entry(query_args)
            else:
                entries = self.keepassxc_db.search(query_args)
                return self.render_search_results(query_keyword, entries, extension)

    def show_active_entry(self, entry):
        items = []
        attrs = self.keepassxc_db.get_entry_details(entry)
        for attr in ["Password", "UserName", "URL", "Notes"]:
            val = attrs.get(attr, "")
            if val:
                action = ActionList(
                    [
                        ExtensionCustomAction(
                            {
                                "action": "show_notification",
                                "summary": "{} copied to the clipboard.".format(attr),
                            }
                        ),
                        CopyToClipboardAction(val),
                    ]
                )

                if attr == "Password":
                    items.append(
                        ExtensionSmallResultItem(
                            icon=CLIP_ICON,
                            name="Copy password to the clipboard",
                            on_enter=action,
                        )
                    )
                else:
                    items.append(
                        ExtensionResultItem(
                            icon=CLIP_ICON,
                            name="{}: {}".format(attr, val),
                            description="Copy {} to the clipboard".format(attr),
                            on_enter=action,
                        )
                    )
        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):
    """ KeywordQueryEventListener class used to manage user input """

    def __init__(self, keepassxc_db):
        self.keepassxc_db = keepassxc_db

    def on_event(self, event, extension):
        try:
            data = event.get_data()
            action = data.get("action", None)
            if action == "read_passphrase":
                return self.read_verify_passphrase(extension)
            elif action == "activate_entry":
                keyword = data.get("keyword", None)
                entry = data.get("entry", None)
                extension.set_active_entry(keyword, entry)
                return SetUserQueryAction("{} {}".format(keyword, entry))
            elif action == "show_notification":
                Notify.Notification.new(data.get("summary")).show()
        except KeepassxcCliNotFoundError:
            return RenderResultListAction([KEEPASSXC_CLI_NOT_FOUND_ITEM])
        except KeepassxcFileNotFoundError:
            return RenderResultListAction([KEEPASSXC_DB_NOT_FOUND_ITEM])
        except KeepassxcCliError as e:
            return RenderResultListAction([keepassxc_cli_error_item(e.message)])

    def read_verify_passphrase(self, extension):
        win = GtkPassphraseEntryWindow(
            verify_passphrase_fn=self.keepassxc_db.verify_and_set_passphrase
        )
        win.read_passphrase()
        if not self.keepassxc_db.need_passphrase():
            Notify.Notification.new("KeePassXC database unlocked.").show()


if __name__ == "__main__":
    Notify.init("ulauncher-keepassxc")
    KeepassxcExtension().run()
    Notify.uninit()

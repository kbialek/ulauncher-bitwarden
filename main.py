import gi

gi.require_version("Notify", "0.7")
from gi.repository import Notify
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import (
    KeywordQueryEvent,
    ItemEnterEvent,
    PreferencesUpdateEvent,
)
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.ActionList import ActionList
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from bitwarden import (
    KeepassxcDatabase,
    KeepassxcCliNotFoundError,
    KeepassxcFileNotFoundError,
    KeepassxcCliError,
)
from gtk_passphrase_entry import GtkPassphraseEntryWindow

SEARCH_ICON = "images/keepassxc-search.svg"
UNLOCK_ICON = "images/keepassxc-search-locked.svg"
EMPTY_ICON = "images/empty.png"
ERROR_ICON = "images/error.svg"
ITEM_ICON = "images/key.svg"
COPY_ICON = "images/copy.svg"
NOT_FOUND_ICON = "images/not_found.svg"

KEEPASSXC_CLI_NOT_FOUND_ITEM = ExtensionResultItem(
    icon=ERROR_ICON,
    name="Cannot find or execute keepassxc-cli",
    description="Please make sure that keepassxc-cli is installed and accessible",
    on_enter=DoNothingAction(),
)

KEEPASSXC_DB_NOT_FOUND_ITEM = ExtensionResultItem(
    icon=ERROR_ICON,
    name="Cannot find the database file",
    description="Please verify the password database file path in extension preferences",
    on_enter=DoNothingAction(),
)

NEED_PASSPHRASE_ITEM = ExtensionResultItem(
    icon=UNLOCK_ICON,
    name="Login to Bitwarden",
    description="Enter passphrase to login the Bitwarden server",
    on_enter=ExtensionCustomAction({"action": "read_passphrase"}),
)

ENTER_QUERY_ITEM = ExtensionResultItem(
    icon=SEARCH_ICON,
    name="Enter search query...",
    description="Please enter your search query",
    on_enter=DoNothingAction(),
)

NO_SEARCH_RESULTS_ITEM = ExtensionResultItem(
    icon=NOT_FOUND_ICON,
    name="No matching entries found...",
    description="Please check spelling or make the query less specific",
    on_enter=DoNothingAction(),
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
        self.subscribe(
            PreferencesUpdateEvent, PreferencesUpdateEventListener(self.keepassxc_db)
        )
        self.active_entry = None

    def get_server_url(self):
        return self.preferences["server-url"]

    def get_email(self):
        return self.preferences["email"]

    def get_max_result_items(self):
        return int(self.preferences["max-results"])

    def get_inactivity_lock_timeout(self):
        return int(self.preferences["inactivity-lock-timeout"])

    def set_active_entry(self, keyword, entry):
        self.active_entry = (keyword, entry)

    def check_and_reset_active_entry(self, keyword, entry):
        r = self.active_entry is not None and self.active_entry[1]["name"] == entry
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
            self.keepassxc_db.initialize(
                extension.get_server_url(),
                extension.get_email(),
                extension.get_inactivity_lock_timeout()
            )

            if self.keepassxc_db.need_login():
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
        max_items = extension.get_max_result_items()
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
                    ExtensionSmallResultItem(icon=ITEM_ICON, name=e["name"], on_enter=action)
                )
            if len(entries) > max_items:
                items.append(more_results_available_item(len(entries) - max_items))
        return RenderResultListAction(items)

    def process_keyword_query(self, event, extension):
        query_keyword = event.get_keyword()
        query_arg = event.get_argument()
        if not query_arg:
            return RenderResultListAction([ENTER_QUERY_ITEM])
        else:
            if extension.check_and_reset_active_entry(query_keyword, query_arg):
                return self.show_active_entry(query_arg)
            else:
                entries = self.keepassxc_db.search(query_arg)
                return self.render_search_results(query_keyword, entries, extension)

    def show_active_entry(self, entry):
        items = []
        details = self.keepassxc_db.get_entry_details(entry)
        attrs = [
            ("password", "password"),
            ("username", "username"),
            ("uri", "URL"),
            ("totp", "totp"),
        ]
        for attr, attr_nice in attrs:
            val = details.get(attr, "")
            if val:
                action = ActionList(
                    [
                        ExtensionCustomAction(
                            {
                                "action": "show_notification",
                                "summary": "{} copied to clipboard.".format(
                                    attr_nice.capitalize()
                                ),
                            }
                        ),
                        CopyToClipboardAction(val),
                    ]
                )

                if attr == "password":
                    items.append(
                        ExtensionResultItem(
                            icon=COPY_ICON,
                            name="{}: ********".format(attr_nice.capitalize()),
                            description="Copy password to clipboard".format(attr_nice),
                            on_enter=action,
                        )
                    )
                else:
                    items.append(
                        ExtensionResultItem(
                            icon=COPY_ICON,
                            name="{}: {}".format(attr_nice.capitalize(), val),
                            description="Copy {} to clipboard".format(attr_nice),
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
                return SetUserQueryAction("{} {}".format(keyword, entry["name"]))
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
        if not self.keepassxc_db.need_login():
            Notify.Notification.new("KeePassXC database unlocked.").show()


class PreferencesUpdateEventListener(EventListener):
    """ Handle preferences updates """

    def __init__(self, keepassxc_db):
        self.keepassxc_db = keepassxc_db

    def on_event(self, event, extension):
        if event.new_value != event.old_value:
            if event.id == "database-path":
                self.keepassxc_db.change_path(event.new_value)
            elif event.id == "inactivity-lock-timeout":
                self.keepassxc_db.change_inactivity_lock_timeout(int(event.new_value))


if __name__ == "__main__":
    Notify.init("ulauncher-keepassxc")
    KeepassxcExtension().run()
    Notify.uninit()

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
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.ActionList import ActionList
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from bitwarden import (
    BitwardenClient,
    BitwardenCliNotFoundError,
    BitwardenCliError,
    BitwardenVaultLockedError)
from gtk_passphrase_entry import GtkPassphraseEntryWindow

BW_CLI_MIN_VERSION = "1.20.0"

SEARCH_ICON = "images/bitwarden-search.svg"
UNLOCK_ICON = "images/bitwarden-search-locked.svg"
EMPTY_ICON = "images/empty.png"
ERROR_ICON = "images/error.svg"
ITEM_ICON = "images/key.svg"
COPY_ICON = "images/copy.svg"
NOT_FOUND_ICON = "images/not_found.svg"

BITWARDEN_CLI_NOT_FOUND_ITEM = ExtensionResultItem(
    icon=ERROR_ICON,
    name="Cannot find or execute bw",
    description="Please make sure that bitwarden-cli is installed and accessible",
    on_enter=DoNothingAction(),
)

NEED_PASSPHRASE_ITEM = ExtensionResultItem(
    icon=UNLOCK_ICON,
    name="Unlock Bitwarden",
    description="Enter passphrase to login/unlock Bitwarden vault",
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


def build_bitwarden_cli_version_unsupported_item(min_version):
    return ExtensionResultItem(
        icon=ERROR_ICON,
        name="Your bw cli version is not supported",
        description="At least version {} is required".format(min_version),
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


def bitwarden_cli_error_item(message):
    return ExtensionResultItem(
        icon=ERROR_ICON,
        name="Error while calling Bitwarden CLI",
        description=message,
        on_enter=DoNothingAction(),
    )

def formatted_result_item(hidden, name, value, action):
    item_description = "Copy {} to clipboard".format(name)

    if hidden:
        item_name = "{}: ********".format(name)
    else:
        item_name = "{}: {}".format(name, value)

    return ExtensionResultItem(
            icon=COPY_ICON,
            name=item_name,
            description=item_description,
            on_enter=action,
        )

def custom_clipboard_actions_list(name, value):
    return [
        ExtensionCustomAction(
            {
                "action": "show_notification",
                "summary": "{} copied to clipboard.".format(
                    name
                ),
            }
        ),
        CopyToClipboardAction(value),
    ]

class BitwardenExtension(Extension):
    """ Extension class, coordinates everything """

    def __init__(self):
        super(BitwardenExtension, self).__init__()
        self.bitwarden = BitwardenClient()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener(self.bitwarden))
        self.subscribe(ItemEnterEvent, ItemEnterEventListener(self.bitwarden))
        self.subscribe(
            PreferencesUpdateEvent, PreferencesUpdateEventListener(self.bitwarden)
        )
        self.active_entry = None

    def get_search_keyword(self):
        return self.preferences["search"]

    def get_sync_keyword(self):
        return self.preferences["sync"]

    def get_lock_keyword(self):
        return self.preferences["lock"]

    def get_server_url(self):
        return self.preferences["server-url"]

    def get_email(self):
        return self.preferences["email"]

    def get_mfa_enabled(self):
        return self.preferences["mfa"] == 'yes'

    def get_max_result_items(self):
        return int(self.preferences["max-results"])

    def get_inactivity_lock_timeout(self):
        return int(self.preferences["inactivity-lock-timeout"])

    def get_session_store_cmd(self):
        return self.preferences["session-store-cmd"]

    def set_active_entry(self, keyword, entry):
        self.active_entry = (keyword, entry)


class KeywordQueryEventListener(EventListener):
    """ KeywordQueryEventListener class used to manage user input """

    def __init__(self, bitwarden):
        self.bitwarden = bitwarden

    def on_event(self, event, extension):
        try:
            self.bitwarden.initialize(
                extension.get_server_url(),
                extension.get_email(),
                extension.get_mfa_enabled(),
                extension.get_inactivity_lock_timeout(),
                extension.get_session_store_cmd()
            )

            if not self.bitwarden.has_session():
                if self.bitwarden.get_bw_version() < BW_CLI_MIN_VERSION:
                    return RenderResultListAction([build_bitwarden_cli_version_unsupported_item(BW_CLI_MIN_VERSION)])
                else:
                    return RenderResultListAction([NEED_PASSPHRASE_ITEM])
            else:
                return self.process_keyword_query(event, extension)
        except BitwardenVaultLockedError:
            return RenderResultListAction([NEED_PASSPHRASE_ITEM])
        except BitwardenCliNotFoundError:
            return RenderResultListAction([BITWARDEN_CLI_NOT_FOUND_ITEM])
        except BitwardenCliError as e:
            return RenderResultListAction([bitwarden_cli_error_item(e.message)])

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
                    ExtensionResultItem(
                        icon=ITEM_ICON,
                        name=e["name"],
                        description=self.bitwarden.get_folder(e["folderId"]),
                        on_enter=action,
                    )
                )
            if len(entries) > max_items:
                items.append(more_results_available_item(len(entries) - max_items))
        return RenderResultListAction(items)

    def process_keyword_query(self, event, extension):
        query_keyword = event.get_keyword()
        query_arg = event.get_argument()

        if query_keyword == extension.get_search_keyword():
            if not query_arg:
                return RenderResultListAction([ENTER_QUERY_ITEM])
            else:
                entries = self.bitwarden.search(query_arg)
                return self.render_search_results(query_keyword, entries, extension)
        elif query_keyword == extension.get_sync_keyword():
            if self.bitwarden.sync():
                Notify.Notification.new("Bitwarden vault synchronized.").show()
            else:
                Notify.Notification.new("Error", "Bitwarden vault synchronization error.").show()
        elif query_keyword == extension.get_lock_keyword():
            if self.bitwarden.lock():
                Notify.Notification.new("Bitwarden vault locked.").show()
            else:
                Notify.Notification.new("Error", "Bitwarden vault locking error.").show()


class ItemEnterEventListener(EventListener):
    """ KeywordQueryEventListener class used to manage user input """

    def __init__(self, bitwarden):
        self.bitwarden = bitwarden

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
                return self.show_active_entry(entry["id"])
            elif action == "show_notification":
                Notify.Notification.new(data.get("summary")).show()
        except BitwardenCliNotFoundError:
            return RenderResultListAction([BITWARDEN_CLI_NOT_FOUND_ITEM])
        except BitwardenCliError as e:
            return RenderResultListAction([bitwarden_cli_error_item(e.message)])

    def read_verify_passphrase(self, extension):
        win = GtkPassphraseEntryWindow(
            login_mode=self.bitwarden.need_login(),
            mfa_enabled=self.bitwarden.need_mfa(),
            verify_passphrase_fn=self.bitwarden.verify_and_set_passphrase
        )
        win.read_passphrase()
        if not self.bitwarden.need_unlock():
            Notify.Notification.new("Bitwarden vault unlocked.").show()

    def show_active_entry(self, entry):
        items = []
        details = self.bitwarden.get_entry_details(entry)
        attrs = [
            ("password", "password"),
            ("username", "username"),
            ("uri", "URL"),
            ("totp", "totp"),
            ("fields", "Custom")
        ]
        for attr, attr_nice in attrs:
            val = details.get(attr, "")
            if val:
                if attr == "fields":
                    for field in val:
                        action = ActionList(
                            custom_clipboard_actions_list(field["name"], field["value"])
                        )

                        if field["type"] == 1:
                            items.append(formatted_result_item(True, field["name"], field["value"], action))
                        else:
                            items.append(formatted_result_item(False, field["name"], field["value"], action))
                else:
                    action = ActionList(
                        custom_clipboard_actions_list(attr_nice.capitalize(), val)
                    )

                if attr == "password":
                    items.append(formatted_result_item(True, attr_nice.capitalize(), val, action))
                elif attr != "fields":
                    items.append(formatted_result_item(False, attr_nice.capitalize(), val, action))
        return RenderResultListAction(items)


class PreferencesUpdateEventListener(EventListener):
    """ Handle preferences updates """

    def __init__(self, bitwarden):
        self.bitwarden = bitwarden

    def on_event(self, event, extension):
        if event.new_value != event.old_value:
            if event.id == "server-url":
                self.bitwarden.change_server_url(event.new_value)
            elif event.id == "email":
                self.bitwarden.change_email(event.new_value)
            elif event.id == "inactivity-lock-timeout":
                self.bitwarden.change_inactivity_lock_timeout(int(event.new_value))
            elif event.id == "session-store-cmd":
                self.bitwarden.change_session_store_cmd(event.new_value)


if __name__ == "__main__":
    Notify.init("ulauncher-bitwarden")
    BitwardenExtension().run()
    Notify.uninit()

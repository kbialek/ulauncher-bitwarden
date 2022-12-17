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
from bitwarden import BitwardenClient, BitwardenCliError, BitwardenVaultLockedError
from gtk_passphrase_entry import GtkPassphraseEntryWindow

SEARCH_ICON = "images/bitwarden-search.svg"
UNLOCK_ICON = "images/bitwarden-search-locked.svg"
EMPTY_ICON = "images/empty.png"
ERROR_ICON = "images/error.svg"
ITEM_ICON = "images/key.svg"
COPY_ICON = "images/copy.svg"
NOT_FOUND_ICON = "images/not_found.svg"

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
                "summary": "{} copied to clipboard.".format(name),
            }
        ),
        CopyToClipboardAction(value),
    ]


class BitwardenExtension(Extension):
    """Extension class, coordinates everything"""

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

    def get_url(self):
        return self.preferences["url"]

    def get_max_result_items(self):
        return int(self.preferences["max-results"])

    def set_active_entry(self, keyword, entry):
        self.active_entry = (keyword, entry)


class KeywordQueryEventListener(EventListener):
    """KeywordQueryEventListener class used to manage user input"""

    def __init__(self, bitwarden):
        self.bitwarden = bitwarden

    def on_event(self, event, extension):
        try:
            self.bitwarden.configure(
                url=extension.get_url(),
            )
            if not self.bitwarden.is_unlocked():
                return RenderResultListAction([NEED_PASSPHRASE_ITEM])
            else:
                return self.process_keyword_query(event, extension)
        except BitwardenVaultLockedError:
            return RenderResultListAction([NEED_PASSPHRASE_ITEM])
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
                Notify.Notification.new(
                    "Error", "Bitwarden vault synchronization error."
                ).show()
        elif query_keyword == extension.get_lock_keyword():
            if self.bitwarden.lock():
                Notify.Notification.new("Bitwarden vault locked.").show()
            else:
                Notify.Notification.new(
                    "Error", "Bitwarden vault locking error."
                ).show()


class ItemEnterEventListener(EventListener):
    """KeywordQueryEventListener class used to manage user input"""

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
        except BitwardenCliError as e:
            return RenderResultListAction([bitwarden_cli_error_item(e.message)])

    def read_verify_passphrase(self, extension):
        win = GtkPassphraseEntryWindow(verify_passphrase_fn=self.bitwarden.unlock)
        win.read_passphrase()
        if self.bitwarden.is_unlocked():
            Notify.Notification.new("Bitwarden vault unlocked.").show()

    def show_active_entry(self, entry):
        items = []
        details = self.bitwarden.get_entry_details(entry)
        attrs = [
            ("password", "password"),
            ("username", "username"),
            ("uri", "URL"),
            ("totp", "totp"),
            ("fields", "Custom"),
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
                            items.append(
                                formatted_result_item(
                                    True, field["name"], field["value"], action
                                )
                            )
                        else:
                            items.append(
                                formatted_result_item(
                                    False, field["name"], field["value"], action
                                )
                            )
                else:
                    action = ActionList(
                        custom_clipboard_actions_list(attr_nice.capitalize(), val)
                    )

                if attr == "password":
                    items.append(
                        formatted_result_item(True, attr_nice.capitalize(), val, action)
                    )
                elif attr != "fields":
                    items.append(
                        formatted_result_item(
                            False, attr_nice.capitalize(), val, action
                        )
                    )
        return RenderResultListAction(items)


class PreferencesUpdateEventListener(EventListener):
    """Handle preferences updates"""

    def __init__(self, bitwarden):
        self.bitwarden = bitwarden

    def on_event(self, event, extension):
        if event.new_value != event.old_value:
            if event.id == "url":
                self.bitwarden.configure(url=event.new_value)


if __name__ == "__main__":
    Notify.init("ulauncher-bitwarden")
    BitwardenExtension().run()
    Notify.uninit()

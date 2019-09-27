import gi
from gi.repository import Gtk, GLib
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

PASSWORD_ICON = "images/icon.svg"
UNLOCK_ICON = "images/icon.svg"


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
    """ Extension class, does the searching """

    def __init__(self):
        super(KeepassxcExtension, self).__init__()
        self.db_passphrase = None
        self.db_path = None
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):
    """ KeywordQueryEventListener class used to manage user input """

    def on_event(self, event, extension):
        actions = []
        if not extension.db_passphrase:
            actions.append(
                ExtensionResultItem(
                    icon=UNLOCK_ICON,
                    name="Unlock KeePassXC database",
                    description="Enter passphrase to unlock the KeePassXC database",
                    on_enter=ExtensionCustomAction("read-verify-passphrase"),
                )
            )
        else:
            actions.append(
                ExtensionResultItem(
                    icon=PASSWORD_ICON,
                    name="yay! {}".format(extension.db_passphrase),
                    description="Got the passphrase!",
                    on_enter=DoNothingAction(),
                )
            )

        return RenderResultListAction(actions)


class ItemEnterEventListener(EventListener):
    """ KeywordQueryEventListener class used to manage user input """

    def on_event(self, event, extension):
        data = event.get_data()
        if data == "read-verify-passphrase":
            self.read_verify_passphrase(extension)

    def read_verify_passphrase(self, extension):
        win = EntryWindow()
        pp = win.read_passphrase()
        print(pp)
        # TODO verify
        extension.db_passphrase = pp


if __name__ == "__main__":
    KeepassxcExtension().run()

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class GtkPassphraseEntryWindow(Gtk.Window):
    def __init__(self, verify_passphrase_fn=None):
        Gtk.Window.__init__(self, title="Enter Passphrase")

        self.verify_passphrase_fn = verify_passphrase_fn

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        self.passphrase = ""
        self.entry = Gtk.Entry()
        self.entry.set_text("")
        self.entry.set_editable(True)
        self.entry.set_visibility(False)
        self.entry.props.max_width_chars = 50
        self.entry.connect("activate", self.enter_pressed)
        self.entry.connect("key-press-event", self.key_pressed)
        vbox.pack_start(self.entry, True, True, 0)

        self.label = Gtk.Label("Enter passphrase")
        vbox.pack_start(self.label, True, True, 0)

        self.set_position(Gtk.WindowPosition.CENTER)

    def close_window(self):
        self.destroy()
        Gtk.main_quit()

    def enter_pressed(self, entry):
        pp = entry.get_text()
        if self.verify_passphrase_fn:
            self.show_verifying_passphrase
            if self.verify_passphrase_fn(pp):
                self.passphrase = pp
                self.close_window()
            else:
                self.show_incorrect_passphrase()
        else:
            self.passphrase = pp
            self.close_window()

    def key_pressed(self, widget, event):
        if event.hardware_keycode == 9:
            self.passphrase = ""
            self.close_window()

    def show_verifying_passphrase(self):
        self.label.set_text("Verifying passphrase...")

    def show_incorrect_passphrase(self):
        self.label.set_markup(
            '<span foreground="red">Incorrect passphrase. Please try again.</span>'
        )
        self.entry.set_text("")

    def read_passphrase(self):
        self.connect("destroy", Gtk.main_quit)
        self.show_all()
        Gtk.main()
        return self.passphrase

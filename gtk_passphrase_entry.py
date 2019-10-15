import os

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class GtkPassphraseEntryWindow(Gtk.Window):
    def __init__(self, login_mode, mfa_enabled, verify_passphrase_fn=None):
        Gtk.Window.__init__(self, title="Bitwarden Login" if login_mode else "Bitwarden Unlock")

        self.set_keep_above(True)
        # self.set_icon_from_file(os.path.dirname(os.path.abspath(__file__)) + "/images/bitwarden.png")
        self.verify_passphrase_fn = verify_passphrase_fn

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        self.pp_label = Gtk.Label("Master Password")
        vbox.pack_start(self.pp_label, True, True, 0)

        self.passphrase = ""
        self.password_entry = Gtk.Entry()
        self.password_entry.set_text("")
        self.password_entry.set_editable(True)
        self.password_entry.set_visibility(False)
        self.password_entry.props.max_width_chars = 50
        self.password_entry.connect("activate", self.enter_pressed)
        self.password_entry.connect("key-press-event", self.key_pressed)
        vbox.pack_start(self.password_entry, True, True, 0)

        self.mfa_label = Gtk.Label("Two Factor Authentication Code")

        self.mfa_entry = Gtk.Entry()
        self.mfa_entry.set_text("")
        self.mfa_entry.set_editable(True)
        self.mfa_entry.set_visibility(True)
        self.mfa_entry.props.max_width_chars = 6
        self.mfa_entry.connect("activate", self.enter_pressed)
        self.mfa_entry.connect("key-press-event", self.key_pressed)
        if login_mode and mfa_enabled:
            vbox.pack_start(self.mfa_label, True, True, 0)
            vbox.pack_start(self.mfa_entry, True, True, 0)

        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)

    def close_window(self):
        self.destroy()
        Gtk.main_quit()

    def enter_pressed(self, entry):
        pp = self.password_entry.get_text()
        mfa = self.mfa_entry.get_text()
        if self.verify_passphrase_fn:
            self.show_verifying_passphrase()
            if self.verify_passphrase_fn(pp, mfa):
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
        self.pp_label.set_text("Verifying passphrase...")

    def show_incorrect_passphrase(self):
        self.pp_label.set_markup(
            '<span foreground="red">Incorrect passphrase. Please try again.</span>'
        )
        self.password_entry.set_text("")

    def read_passphrase(self):
        self.connect("destroy", Gtk.main_quit)
        self.show_all()
        Gtk.main()
        return self.passphrase

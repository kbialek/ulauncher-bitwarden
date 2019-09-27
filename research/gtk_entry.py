import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class EntryWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Enter passphrase")
        self.set_size_request(200, 100)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        self.passphrase = ''
        self.entry = Gtk.Entry()
        self.entry.set_text("")
        self.entry.set_editable(True)
        self.entry.set_visibility(False)
        self.entry.connect("activate", self.enter_pressed)
        self.entry.connect("key-press-event", self.key_pressed)
        vbox.pack_start(self.entry, True, True, 0)

    def enter_pressed(self, widget):
        self.passphrase = widget.get_text()
        Gtk.main_quit()

    def key_pressed(self, widget, event):
        if event.hardware_keycode == 9:
            self.passphrase = ''
            Gtk.main_quit()

    def read_passphrase(self):
        self.connect("destroy", Gtk.main_quit)
        self.show_all()
        Gtk.main()
        return self.passphrase

win = EntryWindow()
pp = win.read_passphrase()
print("Passphrase: " + pp)

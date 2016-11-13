#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
import serial

class Referee:
    def destroy(self, widget, data=None):
        gtk.main_quit()

    def __init__(self):
        self.serial = serial.serial_for_url("/dev/ttyACM0")
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(10)
        self.button_start = gtk.Button("Start")
        self.button_stop = gtk.Button("Stop")
        self.button_start.connect("clicked", self.start, None)
        self.button_stop.connect("clicked", self.stop, None)
        self.box = gtk.VBox(spacing=10)
        self.box.add(self.button_start)
        self.box.add(self.button_stop)
        self.window.add(self.box)
        self.button_start.show()
        self.button_stop.show()
        self.box.show()
        self.window.show()
        
    def start(self, widget, data):
        print("Sending start signal to all")
        self.serial.write("aAXSTART----")
        self.serial.flush()

    def stop(self, widget, data):
        print("Sending stop signal to all")
        self.serial.write("aAXSTOP-----")
        self.serial.flush()

    def main(self):
        gtk.main()

if __name__ == "__main__":
    referee = Referee()
    referee.main()

"""
As OpenCV doesn't handle camera unplugging very well
here is an example using inotify and udev symlinks
"""

import cv2
import os
from threading import Thread, Event
from time import sleep
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class EventHandler(FileSystemEventHandler):
    """
    observer uses inotify to monitor changes in /dev/v4l/by-path
    when corresponding entry appears grabber thread is woken up
    when corresponding entry disappears capture object of grabber is deleted
    """
    def on_created(self, event):
        print "Attached:", event.src_path
        grabber = self.grabbers.get(event.src_path)
        if grabber:
            print "Waking:", grabber
            grabber.enable()
        else:
            print "Ignoring:", event.src_path

    def on_deleted(self, event):
        print "Removed:", event.src_path
        grabber = self.grabbers.get(event.src_path)
        if grabber:
            print "Killing:", grabber
            grabber.disable()
        else:
            print "Ignoring:", event.src_path

handler = EventHandler()
handler.grabbers = {}

observer = Observer()
observer.schedule(handler, "/dev/v4l/by-path", recursive=True)
observer.start()
print("Observer started")

class Grabber(Thread):
    def __init__(self, device):
        print "Starting grabber for:", device
        Thread.__init__(self)

        self.ready = Event() # Used to tell consumers that new frame is available
        self.ready.clear()
        self.wake = Event() # Used by observer to tell grabber that capture device is available
        self.wake.clear()
        
        self.path = os.path.join("/dev/v4l/by-path", device)
        self.daemon = True
        self.running = True
        self.cap = None
        self.blank = np.zeros((480,640,3), dtype=np.uint8)
        self.frame = self.blank
        #self.grab()
        self.start()
        handler.grabbers[self.path] = self # register for inotify

    def run(self):
        while self.running:

            if not self.cap:
                # Check if /dev/v4l/by-path/bla symlink exists
                if not os.path.exists(self.path):
                    print "Waiting for", self.path, "to become available"
                    self.frame = self.blank
                    self.wake.wait() # Wait signal from observer handler
                    self.wake.clear()
                    continue

                canonical = os.path.realpath(self.path)
                assert canonical.startswith("/dev/video")
                assert os.path.exists(canonical)

                node = os.path.basename(canonical)
                
                index = int(node[5:])
                print "Attempting to open: %s (%s)" % (self.path, node)
                self.cap = cv2.VideoCapture(index)
                self.cap.set(3, 640)
                self.cap.set(4, 480)
                self.cap.set(5, 30)


                success, frame = self.cap.read()
                
                if not success:
                    print "Failed to grab frame, trying to reopen capture device"
                    self.cap.release()
                    self.cap = None
                    continue

            success, frame = self.cap.read()
            if success:    
                self.frame = frame
            else:
                self.frame = self.blank

            self.ready.set()


    def stop(self):
        self.running = False
        self.wake.set()
    
    def enable(self):
        self.wake.set()
        
    def disable(self):
        self.cap = None
        self.frame = grabber.blank
        

# To list current device paths: ls /dev/v4l/by-path/
grabbers = [
    Grabber("pci-0000:00:14.0-usb-0:3:1.0-video-index0"), # builtin
    Grabber("pci-0000:00:14.0-usb-0:5:1.0-video-index0"), # right USB port
    Grabber("pci-0000:00:14.0-usb-0:2:1.0-video-index0"), # left USB port
]

print "Grabbers ready"

try:
    while True:
        grabbers[0].ready.wait()        
        cv2.imshow('img', np.hstack([grabber.frame for grabber in grabbers]))
        if cv2.waitKey(1) >= 0:
            break

except KeyboardInterrupt:
    pass
    
for grabber in grabbers:
    print "Stopping grabber:", grabber
    grabber.stop()
print "Stopping filesystem observer"
observer.stop()
        
for grabber in grabbers:
    print "Waiting for grabber to finish:", grabber
    grabber.join()
print "Waiting for filesystem observer to finish"
observer.join()

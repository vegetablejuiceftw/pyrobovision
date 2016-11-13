"""
As OpenCV doesn't handle camera unplugging very well
here is an example using inotify and udev symlinks
"""
from __future__ import print_function

from v4l2 import *
import fcntl
import mmap
import select
import time
import sys
import cv2
import numpy
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
        print("Attached:", event.src_path)
        grabber = self.grabbers.get(event.src_path)
        if grabber:
            print("Waking:", grabber)
            grabber.enable()
        else:
            print("Ignoring:", event.src_path)

    def on_deleted(self, event):
        print("Removed:", event.src_path)
        grabber = self.grabbers.get(event.src_path)
        if grabber:
            print("Killing:", grabber)
            grabber.disable()
        else:
            print("Ignoring:", event.src_path)

handler = EventHandler()
handler.grabbers = {}

observer = Observer()
observer.schedule(handler, "/dev/v4l/by-path", recursive=True)
observer.start()
print("Observer started")

class Grabber(Thread):
    def __init__(self, device):
        print("Starting grabber for:", device)
        Thread.__init__(self)

        self.ready = Event() # Used to tell consumers that new frame is available
        self.ready.clear()
        self.wake = Event() # Used by observer to tell grabber that capture device is available
        self.wake.clear()

        self.path = os.path.join("/dev/v4l/by-path", device)
        self.daemon = True
        self.running = True
        self.vd = None # Video capture descriptor
        self.blank = np.zeros((480,640,3), dtype=np.uint8)
        self.yuv_frame = None
        self.start()
        handler.grabbers[self.path] = self # register for inotify

    def open(self):
        self.vd = open(os.path.realpath(self.path), 'rb+', buffering=0)

        # Query camera capabilities
        cp = v4l2_capability()
        fcntl.ioctl(self.vd, VIDIOC_QUERYCAP, cp)
        self.driver = "".join((chr(c) for c in cp.driver if c))

        # Get current settings
        fmt = v4l2_format()
        fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        fcntl.ioctl(self.vd, VIDIOC_G_FMT, fmt)  # get current settings
        fcntl.ioctl(self.vd, VIDIOC_S_FMT, fmt)  # set whatever default settings we got before

        # Set framerate
        parm = v4l2_streamparm()
        parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        parm.parm.capture.capability = V4L2_CAP_TIMEPERFRAME
        fcntl.ioctl(self.vd, VIDIOC_G_PARM, parm) # get current camera settings
        parm.parm.capture.timeperframe.numerator = 1
        parm.parm.capture.timeperframe.denominator = 30
        fcntl.ioctl(self.vd, VIDIOC_S_PARM, parm)  # change camera capture settings

        # Disable autogain
        if self.driver == "ov534":
            print("Setting gain for:", self.path)
            ctrl = v4l2_control()
            ctrl.id = V4L2_CID_AUTOGAIN
            ctrl.value = 0
            fcntl.ioctl(self.vd, VIDIOC_S_CTRL, ctrl)

            # Set gain to zero
            ctrl = v4l2_control()
            ctrl.id = V4L2_CID_GAIN
            ctrl.value = 0
            fcntl.ioctl(self.vd, VIDIOC_S_CTRL, ctrl)

        # Initalize mmap with dual buffering
        req = v4l2_requestbuffers()
        req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
        req.memory = V4L2_MEMORY_MMAP
        req.count = 2  # nr of buffer frames
        fcntl.ioctl(self.vd, VIDIOC_REQBUFS, req)
        self.buffers = []

        # Setup buffers
        for i in range(req.count):
            buf = v4l2_buffer()
            buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
            buf.memory = V4L2_MEMORY_MMAP
            buf.index = i
            fcntl.ioctl(self.vd, VIDIOC_QUERYBUF, buf)
            mm = mmap.mmap(self.vd.fileno(), buf.length, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=buf.m.offset)
            self.buffers.append(mm)
            fcntl.ioctl(self.vd, VIDIOC_QBUF, buf)


        # Start streaming
        fcntl.ioctl(self.vd, VIDIOC_STREAMON, v4l2_buf_type(V4L2_BUF_TYPE_VIDEO_CAPTURE))

        # Wait cameras to get ready
        t0 = time.time()
        max_t = 1
        ready_to_read, ready_to_write, in_error = ([], [], [])
        while len(ready_to_read) == 0 and time.time() - t0 < max_t:
            ready_to_read, ready_to_write, in_error = select.select([self.vd], [], [], max_t)

    @property
    def hsv(self):
        """
        Convenience function, inRange against yuv_frame should be used instead
        """
        if self.yuv_frame is None:
            return self.blank
        if self._cached_hsv_frame is None:
            self._cached_hsv_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)
        return self._cached_hsv_frame

    @property
    def frame(self):
        """
        Get RGB encoded frame and store it for later
        """
        if self.yuv_frame is None:
            return self.blank
        if self._cached_rgb_frame is None:
            self._cached_rgb_frame = cv2.cvtColor(self.yuv_frame, cv2.COLOR_YUV2BGR_YUYV)
        return self._cached_rgb_frame

    def run(self):
        while self.running:

            if not self.vd:
                # Check if /dev/v4l/by-path/bla symlink exists
                if not os.path.exists(self.path):
                    print("Waiting for", self.path, "to become available")
                    self.yuv_frame = None
                    self.wake.wait() # Wait signal from observer handler
                    self.wake.clear()
                    continue

                self.open()


            # get image from the driver queue
            try:
                buf = v4l2_buffer()
                buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
                buf.memory = V4L2_MEMORY_MMAP
                fcntl.ioctl(self.vd, VIDIOC_DQBUF, buf)
                mm = self.buffers[buf.index]
                if sys.version_info[0] == 3:
                    self.yuv_frame = np.asarray(mm, dtype=np.uint8).reshape((480, 640, 2))
                else: # Fallback for python2
                    self.yuv_frame = np.fromstring(mm, dtype=np.uint8).reshape((480, 640, 2))
                fcntl.ioctl(self.vd, VIDIOC_QBUF, buf)  # requeue the buffer
            except (OSError, ValueError, IOError):
                # Camera unplugged
                self.yuv_frame = None
                self.vd.close()
            finally:
                # Invalidate cached frames
                self._cached_rgb_frame = None
                self._cached_hsv_frame = None

            # Signal consumer(s)
            self.ready.set()

        # Graceful shutdown
        if self.vd:
            fcntl.ioctl(self.vd, VIDIOC_STREAMOFF, v4l2_buf_type(V4L2_BUF_TYPE_VIDEO_CAPTURE))
            self.vd.close()


    def stop(self):
        self.running = False
        self.wake.set()

    def enable(self):
        self.wake.set()

    def disable(self):
        self.vd = None
        self.yuv_frame = self.blank
        self._cached_rgb_frame = None

if __name__ == "__main__":
    # To list current device paths: ls /dev/v4l/by-path/
    grabbers = [
        Grabber("pci-0000:00:14.0-usb-0:3:1.0-video-index0"), # builtin
        Grabber("pci-0000:00:14.0-usb-0:5:1.0-video-index0"), # right USB port
        Grabber("pci-0000:00:14.0-usb-0:2:1.0-video-index0"), # left USB port
    ]

    print("Grabbers ready")

    try:
        while True:
            grabbers[0].ready.wait()
            cv2.imshow('img', np.hstack([grabber.frame for grabber in grabbers]))
            if cv2.waitKey(1) >= 0:
                break

    except KeyboardInterrupt:
        pass

    for grabber in grabbers:
        print("Stopping grabber:", grabber)
        grabber.stop()
    print("Stopping filesystem observer")
    observer.stop()

    for grabber in grabbers:
        print("Waiting for grabber to finish:", grabber)
        grabber.join()
    print("Waiting for filesystem observer to finish")
observer.join()

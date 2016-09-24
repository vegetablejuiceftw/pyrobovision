import select
import v4l2capture
from time import time, sleep
import numpy
import cv2

# https://github.com/gebart/python-v4l2capture/blob/master/capture_video.py
class Grabber:

    def __init__(self, width, height, fps, key = 0 ):
        
        self.width, self.height = width, height
        self.size = self.width * self.height * 2
        
        # Open the video device.
        video = v4l2capture.Video_device("/dev/video{}".format(key))

        # Suggest an image size to the device. The device may choose and
        # return another size if it doesn't support the suggested one.
        print(video.set_format(width, height, yuv420=1, fourcc="YUYV"))
        print(video.get_info())
        print(video.set_fps(fps))

        # Create a buffer to store image data in. This must be done before
        # calling 'start' if v4l2capture is compiled with libv4l2. Otherwise
        # raises IOError.
        print(video.create_buffers(5))

        # Send the buffer to the device. Some devices require this to be done
        # before calling 'start'.
        print(video.queue_all_buffers())

        # Start the device. This lights the LED if it's a camera that has one.
        video.start()

        self.video = video

        self.uv, self.data = None, None       
    
    def read(self):
        select.select((self.video,), (), ())
        image_data = self.video.read_and_queue()        
        self.data = numpy.frombuffer(image_data, dtype=numpy.uint8)
        if self.data.shape[0] != self.size:
            return self.read()
        U = self.data[1::4].reshape((self.height, self.width//2, 1))
        V = self.data[3::4].reshape((self.height, self.width//2, 1))
        self.uv = numpy.dstack((U,V))
        return self.uv
        
    @property
    def image(self):
        U = self.data[1::4].repeat(2).reshape((self.height, self.width, 1))
        V = self.data[3::4].repeat(2).reshape((self.height, self.width, 1))
        Y = self.data[0::2].reshape((self.height, self.width, 1)) 
        return numpy.dstack((Y,U,V))
        
if __name__ == '__main__':
    grabber = Grabber(640, 480)
    for i in range(60):
        start = time()
        frame = grabber.read()
        print(time()-start)    

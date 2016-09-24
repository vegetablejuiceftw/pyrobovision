from time import *
import io
import numpy as np
import cv2
from multiprocessing import *
from multiprocessing import sharedctypes,Value
from tempfile import mkdtemp
import os.path as path

from ass import Grabber

SAMPLE_SIZE = 200
class FrameGrabber(Process):
    def __init__(self, fp,COUNTER):
        super(FrameGrabber, self).__init__()
        self.current_frame = fp
        self.camera = None
        self.scan_times = [0] * SAMPLE_SIZE
        self.missed_count = 0
            
    def run(self):
        camera = Grabber(RES[0], RES[1], FPS)
        while True:
            start = time()
            B = camera.read()
            A = self.current_frame
            np.copyto(A,B)

            self.missed_count += COUNTER.value - TAKEN_COUNTER.value
            COUNTER.value += 1

            if not COUNTER.value % 200:
                fps = SAMPLE_SIZE/sum(self.scan_times)
                factor = self.missed_count/COUNTER.value
                real_fps = fps * (1-factor)
                print("real:{:.1f}, fps:{:.4f}, frame#:{}, factor:real:{:.4f}".format(real_fps, fps,COUNTER.value,factor))

            self.scan_times[COUNTER.value % SAMPLE_SIZE] = time() - start

            
from random import randint
class Worker(Process):
    def __init__(self, fp,COUNTER,name='Not named worker'):
        super(Worker, self).__init__()
        self.frame_pointer = fp
        self.COUNTER = COUNTER
        self.name = name

    def run(self):
        temp_array = np.zeros(SHAPE,dtype='uint8')
        while True:
            start = time()
            TEMP_COUNTER = self.COUNTER.value
            if TAKEN_COUNTER.value < TEMP_COUNTER:
                with TAKEN_COUNTER.get_lock():
                    TAKEN_COUNTER.value = TEMP_COUNTER
            else:

                sleep(0.0001 * randint(8,15) * 2)
                continue           

            np.copyto(temp_array,self.frame_pointer)         
            blurred_uv = cv2.blur(temp_array, (4,4))  

            # mask = cv2.inRange(blurred_uv, (60, 160), (90, 255))  ## FILTER THE COLORS!!           
            mask = cv2.inRange(blurred_uv, (0, 0), (90, 255))  ## FILTER THE COLORS!!           
            mask = cv2.dilate(mask, None, iterations=2)
            cnts = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
            if cnts:
                contour = max(cnts, key=cv2.contourArea)   
                print(cv2.minEnclosingCircle(contour))            

            #cv2.imwrite('derp_{}.jpg'.format(self.name), mask)
 

COUNTER = Value('i', 0)
TAKEN_COUNTER = Value('i', 0)


RES = (320, 240)
RES = (640, 480)
FPS = 199
FPS = 59
SHAPE = (RES[1],RES[0]//2,2)
FILE_NAME = path.join(mkdtemp(), 'test.array')

if __name__ == '__main__':
    freeze_support()
    fp = np.memmap(FILE_NAME, dtype='uint8', mode='w+', shape=SHAPE)

    grabber = FrameGrabber(fp,COUNTER)
    grabber.start()
    sleep(0.5)    

    fp = np.memmap(FILE_NAME, dtype='uint8', mode='r+', shape=SHAPE)

    for i in range(3): 
        grabber = Worker(fp,COUNTER,name='W'+str(i))
        grabber.start()

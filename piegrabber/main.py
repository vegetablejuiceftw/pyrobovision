import cv2
import numpy
from time import time, sleep
from threading import Thread, Event

from flask import Flask, render_template, Response, request

from camera import Grabber
from process import process

class FrameThread(Thread):
    def __init__(self, width=640, height=480, capture_rate=50, key=0):
        Thread.__init__(self)
        self.width, self.height, self.capture_rate = width, height, capture_rate
        self.daemon = True        
        self.frame = None       
        self.start()
        self.fps, self.center, self.radius= 0, None, None
    
    def run(self):
        grabber = Grabber(self.width, self.height, self.capture_rate)
        c = 0
        start = time()
        while True:
            
            uv = grabber.read()            
            
            result = process(uv)
            
            c+=1
            if not c%60:
                ms = (time()-start)/60
                self.fps = round(1 / (ms)), round(ms,4 )
                start = time()

                print(self.fps, result['ms'])
                self.frame = numpy.hstack([cv2.cvtColor(result['masks'][0], cv2.COLOR_GRAY2RGB), grabber.image])
                     
            
            
camera = FrameThread()
# camera = FrameThread(width=320,height=240,capture_rate=200)

# sleep(40)

app = Flask(__name__)
SLEEP_TIME = 0.09

@app.route('/')
def both():
    def generator():
        while True:
            frame = camera.frame
            try:
                frame = cv2.resize(frame, (0,0), fx=0.5, fy=0.5) 
                ret, jpeg = cv2.imencode('.jpg', frame, (cv2.IMWRITE_JPEG_QUALITY, 70))
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
                print('fps {} center {}'.format(camera.fps, camera.center))
            except:
                pass
            sleep(SLEEP_TIME)
    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, use_reloader=False, threaded=True)

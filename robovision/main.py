from __future__ import print_function
from time import sleep
import json
import cv2
from threading import Thread, Event
import signal
import numpy as np
from flask import Flask, render_template, Response, request
import asyncio
import websockets
import os


# try to load motor
from camera import CameraMaster
from nutgobbler import BrainFuck
from pymatamotor import Motor

motor_driver = Motor()

# try to load brains
brainfuck = BrainFuck(motor_driver)

# try to load cameruhs
cameras = CameraMaster(brainfuck)
print('Cameras working:', cameras.slave_count)


# initiate web services
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
SLEEP_TIME = 0.08
flask_running = True

from datetime import datetime

class Recorder(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.wake = Event()
        self.running = False

    def run(self):
        while True:
            print("recorder waiting for wake signal")
            self.wake.wait()
            then = datetime.now()
            path = os.path.expanduser("~/bot-%s.avi") % datetime.now().strftime("%Y%m%d%H%M%S")

            fourcc = cv2.VideoWriter_fourcc(*'XVID')

            writer = cv2.VideoWriter(path, fourcc, 30, (480*8, 640))
            while self.running:
                cameras.slaves[0].frame_grabbed.wait()
                frames = []
                for index in range(0,8):
                    slave = cameras.slaves[index]
                    frames.append(slave.rgb_frame)
                writer.write(np.rot90(np.vstack(frames), 3))
            writer.release()
            print("Recorder saved %s of video to %to:", datetime.now()-then, path)

    def enable(self):
        self.running = True
        self.wake.set()
        print("Enabling recording")

    def disable(self):
        self.wake.clear()
        self.running = False
        print("Disabled recording")

    def toggle(self):
        if self.running:
            self.disable()
        else:
            self.enable()

recorder = Recorder()
recorder.start()


@app.route('/combined/<path:type_str>')
def video_combined(type_str):
    TYPES = ['VIDEO', 'DEBUG', 'COMBO']

    def generator():
        while flask_running:
            last_frame = cameras.get_group_photo(mode=TYPES.index(type_str.upper()))
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(SLEEP_TIME)
    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def group():
    return render_template('group.html', camera_list=cameras.get_slaves_list())

# static files for js and css
@app.route('/nouislider.css')
def nouisliderCSS():
    return render_template('nouislider.css')


@app.route('/nouislider.js')
def nouisliderJS():
    return render_template('nouislider.js')


@app.route('/config/camera/<path:camera_id>', methods=['get', 'post'])
def config(camera_id):
    camera_id = int(camera_id)
    channel = request.form.get('channel')
    LOWER = int(request.form.get('LOWER'))
    UPPER = int(request.form.get('UPPER'))
    print('config', channel, LOWER, UPPER)

    data = {"channel": (channel, LOWER, UPPER)}
    cameras.set_slave_properties(camera_id, data)

    return 'Mkay, yes, a response, I guess I can do that.'


@app.route('/iter/<path:camera_id>', methods=['get', 'post'])
def iter(camera_id):
    camera_id = int(camera_id)

    return str(cameras.set_slave_properties(camera_id, {"order": -1}))


class Bread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()

    def run(self):
        print("bread start")
        app.run(host='0.0.0.0', debug=True, use_reloader=False, threaded=True)

    def close(self):
        pass  # no wai to kill
        # app.stop(timeout=5)


server = Bread()

# handle shut down signals, as this is a threaded mess of a system
def signal_handler(sig, frame):
    global flask_running
    motor_driver.close()
    flask_running = False
    server.close()
    cameras.close()
    exit(0)

signal.signal(signal.SIGINT, signal_handler)


# initiate web sockets

async def time(websocket, path):
    last = None
    while True:
        try:
            await websocket.send("hello")
            command = await websocket.recv()
            response = json.loads(command)
        except:
            print("Did it dieded? :(")
            break
        action = response.pop("action")
        if action == "gamepad":
            for k in response:
                #print("K:", k)
                gamepad = response[k]

                axis = gamepad.get("axis",  {})
                a, b, right_joystick_x, d, e, f = [axis.get(j, 0) for j in "012345"]

                button = gamepad.get("button", {})
                kicker = any([button.get(key, [False, False])[0] for key in '45']) # left-4 & right-5 trigger

                MODE_A = button.get("7", [False, False])[0]
                MODE_B = button.get("6", [False, False])[0]

                data = {
                    'K': kicker,
                    "M_A": MODE_A,
                    "M_B": MODE_B,
                    "TYPE": "A",
                }
                if (a, b, right_joystick_x) != last:
                    data.update( {
                        'Fw': -right_joystick_x,
                        'Fx': -a, # joysticks are weird
                        'Fy': -b,
                    })
                last = (a, b, right_joystick_x)
                # print("\t\tFx{Fx:.4f}\tFy:{Fy:.4f}\tR:{Fw:.4f}".format(**data))
                motor_driver.load_data(data)
        elif action == "record_toggle":
            recorder.toggle()
        elif action == "record_enable":
            recorder.enable()
        elif action == "record_disable":
            recorder.disable()
        else:
            print("Unhandled action:", action)
        sleep(0.004)


start_server = websockets.serve(time, '0.0.0.0', 5001)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()

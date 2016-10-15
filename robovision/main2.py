from __future__ import print_function
from threading import Thread
from time import sleep
import imp
import json
import os
import cv2
import numpy

from PyMata.pymata import PyMata
from threading import Thread, Event
import signal

from flask import Flask, render_template, Response, request

from flask_socketio import SocketIO, emit

import asyncio
import websockets

from pymatamotor import Motor
from camera import CameraMaster
from nutgobbler import BallSucker

# try to load motor 
motor_driver = Motor()

# try to load brains
BallSucker(motor_driver)

# try to load cameruhs
cameras = CameraMaster()
print('Cameras working:', cameras.slave_count)

# handle shut down signals, as this is a threaded mess of a system
server = None


def signal_handler(sig, frame):
    motor_driver.close()
    server.close()
    cameras.close()
    exit(signal.SIGTERM)


signal.signal(signal.SIGINT, signal_handler)

# initiate web services

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
SLEEP_TIME = 0.08


@app.route('/combined/<path:type_str>')
def video_combined(type_str):
    TYPES = ['VIDEO', 'DEBUG', 'COMBO']

    def generator():
        while True:
            last_frame = cameras.get_group_photo(mode=TYPES.index(type_str.upper()))
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(SLEEP_TIME)

    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video/<path:camera_id>')
def video(camera_id):
    camera_id = int(camera_id)

    def generator():
        while True:
            last_frame = cameras.get_slave_photo(camera_id)
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(SLEEP_TIME)

    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/debug/<path:camera_id>')
def debug(camera_id):
    camera_id = int(camera_id)

    def generator():
        while True:
            last_frame = cameras.get_slave_photo(camera_id, mode=CameraMaster.DEBUG_MODE)
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(SLEEP_TIME)

    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/both/<path:camera_id>')
def both(camera_id):
    camera_id = int(camera_id)

    def generator():
        while True:
            last_frame = cameras.get_slave_photo(camera_id, mode=CameraMaster.COMBO_MODE)
            ret, jpeg = cv2.imencode('.jpg', last_frame, (cv2.IMWRITE_JPEG_QUALITY, 80))
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tostring() + b'\r\n\r\n'
            sleep(SLEEP_TIME)

    return Response(generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return render_template('main.html', camera_list=cameras.get_slaves_list())


@app.route('/group')
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


# initiate web sockets

async def time(websocket, path):
    while True:
        try:
            await websocket.send("hello")
            command = await websocket.recv()
            response = json.loads(command)
        except:
            print("Did it dieded? :(")
            break

        for k in response:
            gamepad = response[k]

            axis = gamepad.get("axis")
            if not axis:
                continue

            a, b, right_joystick_x, d, e, f = [axis.get(j, 0) for j in "012345"]

            data = {
                'Fw': right_joystick_x,
                'Fx': a,
                'Fy': b,
            }
            # print("\t\tFx{Fx:.4f}\tFy:{Fy:.4f}\tR:{R:.4f}".format(**data))
            motor_driver.load_data(data)


start_server = websockets.serve(time, '0.0.0.0', 5001)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()

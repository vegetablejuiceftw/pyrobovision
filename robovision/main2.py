from __future__ import print_function
from flask import Flask, render_template
from flask_sockets import Sockets
from threading import Thread
from time import sleep
import imp
import json
import os



from PyMata.pymata import PyMata
from threading import Thread, Event
import signal


# Motor pins on Arduino
MOTOR_1_PWM = 11
MOTOR_2_PWM = 10
MOTOR_3_PWM = 9

MOTOR_1_A   = 4
MOTOR_2_A   = 6
MOTOR_3_A   = 5

MOTOR_1_B   = 7
MOTOR_2_B   = 3
MOTOR_3_B   = 2


def signal_handler(sig, frame):
    board.reset()

# Here we initialize the motor pins on Arduino
board = PyMata(bluetooth=False)
signal.signal(signal.SIGINT, signal_handler)
board.set_pin_mode(MOTOR_1_PWM, board.PWM,    board.DIGITAL)
board.set_pin_mode(MOTOR_1_A,   board.OUTPUT, board.DIGITAL)
board.set_pin_mode(MOTOR_1_B,   board.OUTPUT, board.DIGITAL)
board.set_pin_mode(MOTOR_2_PWM, board.PWM,    board.DIGITAL)
board.set_pin_mode(MOTOR_2_A,   board.OUTPUT, board.DIGITAL)
board.set_pin_mode(MOTOR_2_B,   board.OUTPUT, board.DIGITAL)
board.set_pin_mode(MOTOR_3_PWM, board.PWM,    board.DIGITAL)
board.set_pin_mode(MOTOR_3_A,   board.OUTPUT, board.DIGITAL)
board.set_pin_mode(MOTOR_3_B,   board.OUTPUT, board.DIGITAL)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sockets = Sockets(app)

@app.route('/')
def index():
    print("HTTP request")
    return render_template('main.html')

@sockets.route('/')
def command(ws):
    while not ws.closed:
        command = ws.receive()

        gamepad = json.loads(command)["0"]
        axis = gamepad.pop("axis")
        print(axis)
        a,b,c,d,e,f = [int(j*255) for j in [axis["0"], axis["1"], axis["2"], axis["3"], axis["4"], axis["5"]]]


        print(a,b,c,d,e,f)


        board.analog_write(MOTOR_1_PWM, 0)
        board.analog_write(MOTOR_2_PWM, 0)
        board.analog_write(MOTOR_3_PWM, 0)


        board.digital_write(MOTOR_1_B, 0)
        board.digital_write(MOTOR_1_A, 0)
        board.digital_write(MOTOR_2_B, 0)
        board.digital_write(MOTOR_2_A, 0)
        board.digital_write(MOTOR_3_B, 0)
        board.digital_write(MOTOR_3_A, 0)


        # Set directions
        board.digital_write(MOTOR_1_A, c < 0)
        board.digital_write(MOTOR_1_B, c > 0)
        board.digital_write(MOTOR_2_A, c < 0)
        board.digital_write(MOTOR_2_B, c > 0)
        board.digital_write(MOTOR_3_A, c < 0)
        board.digital_write(MOTOR_3_B, c > 0)

        # Set duty cycle
        board.analog_write(MOTOR_1_PWM, 255-max(25, abs(c)))
        board.analog_write(MOTOR_2_PWM, 255- max(25, abs(c)))
        board.analog_write(MOTOR_3_PWM, 255-max(25, abs(c)))



def main():
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    ip, port = ('0.0.0.0', 5001)
    if os.getuid() == 0:
        port = 80
    app.debug = True
    server = pywsgi.WSGIServer((ip, port), app, handler_class=WebSocketHandler)
    print("Starting server at http://{}:{}".format(ip, port))
    server.serve_forever()

if __name__ == '__main__':
    main()

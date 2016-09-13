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


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sockets = Sockets(app)

@app.route('/')
def index():
    print("HTTP request")
    return render_template('main.html')


class Motor(Thread):
    def __init__(self,*args,**kwargs):
        Thread.__init__(self)
        self.daemon = True
        self.running = False
        self.board = None
        self.data = {}
        self.start()

    def load_data(self, data):
        self.data = data

    def setup_pymata(self):
        # Here we initialize the motor pins on Arduino
        board = PyMata(bluetooth=False)        
        board.set_pin_mode(MOTOR_1_PWM, board.PWM,    board.DIGITAL)
        board.set_pin_mode(MOTOR_1_A,   board.OUTPUT, board.DIGITAL)
        board.set_pin_mode(MOTOR_1_B,   board.OUTPUT, board.DIGITAL)
        board.set_pin_mode(MOTOR_2_PWM, board.PWM,    board.DIGITAL)
        board.set_pin_mode(MOTOR_2_A,   board.OUTPUT, board.DIGITAL)
        board.set_pin_mode(MOTOR_2_B,   board.OUTPUT, board.DIGITAL)
        board.set_pin_mode(MOTOR_3_PWM, board.PWM,    board.DIGITAL)
        board.set_pin_mode(MOTOR_3_A,   board.OUTPUT, board.DIGITAL)
        board.set_pin_mode(MOTOR_3_B,   board.OUTPUT, board.DIGITAL)
        self.board = board
    
    def close(self):
        self.board.reset()
        self.running = False
    
    def run(self):
        print("START MOTOR THREAD")
        self.setup_pymata()
        print("LOADED PYMATA")
        self.running = True
        while self.running:
            sleep(0.008)

            rotate = self.data.get('rotate')
            print('rotate>?', rotate)
            
            continue
            board = self.board

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
            
        
motor_driver = Motor()
server = None

def shutdown():
  print('Shutting down ...')
  server.stop(timeout=5)
  exit(signal.SIGTERM)

def signal_handler(sig, frame):
    motor_driver.close()
    shutdown()
    
signal.signal(signal.SIGINT, signal_handler)

@sockets.route('/')
def command(ws):
    while not ws.closed:
        command = ws.receive()
        response = json.loads(command) 
        if not response:
            continue
        gamepad = response.values()[0]
        
        axis = gamepad.get("axis")
        if not axis:
            continue      

        a,b,right_joystick_x,d,e,f = [int(axis.get(j,0)*255) for j in "012345"]

        print(a,b,right_joystick_x,d,e,f)
        
        motor_driver.load_data({'rotate':right_joystick_x})

import gevent
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

def main():
    global server
       
    #from gevent.pool import Pool
    #pool_size = 8
    #worker_pool = Pool(pool_size) server->spawn=worker_pool
    
    ip, port = ('0.0.0.0', 5001)
    if os.getuid() == 0:
        port = 80
    app.debug = True
    server = pywsgi.WSGIServer((ip, port), app, handler_class=WebSocketHandler)
    print("Starting server at http://{}:{}".format(ip, port))
    server.serve_forever()

if __name__ == '__main__':
    main()

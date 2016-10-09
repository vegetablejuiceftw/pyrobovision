from __future__ import print_function
from threading import Thread
from time import sleep
import imp
import json
import os

import numpy

from PyMata.pymata import PyMata
from threading import Thread, Event
import signal

from flask import Flask, render_template
from flask_socketio import SocketIO, emit


# try to load motor 
# from pymatamotor import Motor
# motor_driver = Motor()


# handle shut down signals, as this is a threaded mess of a system
server = None

def shutdown():
  print('Shutting down ...')
  server.stop(timeout=5)
  exit(signal.SIGTERM)

def signal_handler(sig, frame):
    motor_driver.close()
    shutdown()
    
signal.signal(signal.SIGINT, signal_handler)



# initiate web services 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'


@app.route('/')
def index():
    print("HTTP request")
    return render_template('main.html')
   


from threading import Thread, Event

class Bread(Thread):
    def __init__(self):        
        Thread.__init__(self)
        self.daemon = True
        self.start()

    def run(self):
        print("bread start")
        app.run(host='0.0.0.0', debug=True, use_reloader=False, threaded=True)

if __name__ == '__main__':
    Bread()




import asyncio
import websockets

async def time(websocket, path):
    while True:
        try:
            await websocket.send("hello")
            greeting = await websocket.recv()
            print("< {}".format(greeting))
            # await asyncio.sleep(0.01)
        except:
            print("Did it dieded? :(")
            break

start_server = websockets.serve(time, '0.0.0.0', 5001)


print("SOCKS")

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()



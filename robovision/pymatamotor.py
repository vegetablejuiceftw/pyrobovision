import numpy
import signal
import serial
from threading import Thread
from time import sleep
from PyMata.pymata import PyMata


class Motor(Thread):
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

    def __init__(self,*args,**kwargs):
        Thread.__init__(self)
        self.daemon = True
        self.running = False
        self.mock_mode = False
        self.board = None
        self.data = {}
        self.last_direction = None
        self.start()

    def load_data(self, data):
        self.data = data

    def setup_pymata(self):
        # Here we initialize the motor pins on Arduino
        try:
            board = PyMata(bluetooth=False)        
            board.set_pin_mode(self.MOTOR_1_PWM, board.PWM,    board.DIGITAL)
            board.set_pin_mode(self.MOTOR_1_A,   board.OUTPUT, board.DIGITAL)
            board.set_pin_mode(self.MOTOR_1_B,   board.OUTPUT, board.DIGITAL)
            board.set_pin_mode(self.MOTOR_2_PWM, board.PWM,    board.DIGITAL)
            board.set_pin_mode(self.MOTOR_2_A,   board.OUTPUT, board.DIGITAL)
            board.set_pin_mode(self.MOTOR_2_B,   board.OUTPUT, board.DIGITAL)
            board.set_pin_mode(self.MOTOR_3_PWM, board.PWM,    board.DIGITAL)
            board.set_pin_mode(self.MOTOR_3_A,   board.OUTPUT, board.DIGITAL)
            board.set_pin_mode(self.MOTOR_3_B,   board.OUTPUT, board.DIGITAL)
            self.board = board
            self.running = True
        except (serial.serialutil.SerialException, FileNotFoundError) as err:
            print("# Something wrong with the serial device:{}".format(err))
            print("# Running in MOCK mode")
            self.mock_mode = True
    
    def close(self):
        if self.board:
            self.board.reset()
        self.running = False
        self.mock_mode = False
        print("# Motor killed")

    def get_xyw(self):
        return self.data.get('Fx',0), self.data.get('Fy',0), self.data.get('R',0)

    def translate(self):
        Fx, Fy, Fw = self.get_xyw()

        matrix = [[0.58, -0.58, 0],[-0.33, -0.33, 0.67],[0.33,0.33,0.33]]
        matrix = [[0.58, -0.33, 0.33],[-0.58, -0.33, 0.33],[0,0.67,0.33]]
        
        Fa, Fb, Fc = numpy.dot(matrix,[Fx,Fy,Fw])        

        return Fa, Fb, Fc
    
    def run(self):
        print("# START MOTOR THREAD")
        self.setup_pymata()
        print("# LOADED PYMATA")

        last = ()
        while self.mock_mode:
            Fa, Fb, Fc = self.translate()
            if self.last_direction != (Fa, Fb, Fc):
                #print("INPUT:  {:.4f} {:.4f} {:.4f}".format(*self.get_xyw()))
                print("RESULT: {:.4f} {:.4f} {:.4f}".format(Fa,Fb,Fc))
            self.last_direction = (Fa, Fb, Fc)
            sleep(0.02)
        
        while self.running:
            sleep(0.012)
             
            Fa, Fb, Fc = self.translate()
            if self.last_direction == (Fa, Fb, Fc):
                continue
            self.last_direction = (Fa, Fb, Fc)
            print("RESULT: {:.4f} {:.4f} {:.4f}".format(Fa,Fb,Fc))

            # reset things TODO: wai thou?
            self.board.analog_write(self.MOTOR_1_PWM, 0)
            self.board.analog_write(self.MOTOR_2_PWM, 0)
            self.board.analog_write(self.MOTOR_3_PWM, 0)


            self.board.digital_write(self.MOTOR_1_B, 0)
            self.board.digital_write(self.MOTOR_1_A, 0)
            self.board.digital_write(self.MOTOR_2_B, 0)
            self.board.digital_write(self.MOTOR_2_A, 0)
            self.board.digital_write(self.MOTOR_3_B, 0)
            self.board.digital_write(self.MOTOR_3_A, 0)

            # Set directions
            self.board.digital_write(self.MOTOR_1_A, Fa < 0)
            self.board.digital_write(self.MOTOR_1_B, Fa > 0)
            self.board.digital_write(self.MOTOR_2_A, Fb < 0)
            self.board.digital_write(self.MOTOR_2_B, Fb > 0)
            self.board.digital_write(self.MOTOR_3_A, Fc < 0)
            self.board.digital_write(self.MOTOR_3_B, Fc > 0)

            # Set duty cycle
            self.board.analog_write(self.MOTOR_1_PWM, 255-max(25, abs(int(float(Fa)*255))))
            self.board.analog_write(self.MOTOR_2_PWM, 255-max(25, abs(int(float(Fb)*255))))
            self.board.analog_write(self.MOTOR_3_PWM, 255-max(25, abs(int(float(Fc)*255))))

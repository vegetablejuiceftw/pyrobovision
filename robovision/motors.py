from PyMata.pymata import PyMata
from threading import Thread, Event
import signal


# Motor pins on Arduino
MOTOR_1_PWM = 2
MOTOR_1_A   = 3
MOTOR_1_B   = 4
MOTOR_2_PWM = 5
MOTOR_2_A   = 6
MOTOR_2_B   = 7
MOTOR_3_PWM = 8
MOTOR_3_A   = 9
MOTOR_3_B   = 10

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

class MotorThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.lock = Event()
        self.set(0, 0, 0)

    def set(self, m1, m2, m3):
        self.m1, self.m2, self.m3 = m1, m2, m3
        self.lock.set()

    def run(self):
        while True:
            # Reset all direction pins to avoid damaging H-bridges
            board.digital_write(MOTOR_1_B, 0)
            board.digital_write(MOTOR_1_A, 0)
            board.digital_write(MOTOR_2_B, 0)
            board.digital_write(MOTOR_2_A, 0)
            board.digital_write(MOTOR_3_B, 0)
            board.digital_write(MOTOR_3_A, 0)

            # Set duty cycle
            board.analog_write(MOTOR_1_PWM, int(abs(self.m1) + 25) if self.m1 else 0)
            board.analog_write(MOTOR_2_PWM, int(abs(self.m2) + 25) if self.m2 else 0)
            board.analog_write(MOTOR_3_PWM, int(abs(self.m3) + 25) if self.m3 else 0)

            # Set directions
            board.digital_write(MOTOR_1_A, self.m1 < 0)
            board.digital_write(MOTOR_1_B, self.m1 > 0)
            board.digital_write(MOTOR_2_A, self.m2 < 0)
            board.digital_write(MOTOR_2_B, self.m2 > 0)
            board.digital_write(MOTOR_3_A, self.m3 < 0)
            board.digital_write(MOTOR_3_B, self.m3 > 0)
            self.lock.wait()
            self.lock.clear()
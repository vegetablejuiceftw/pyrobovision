MOTOR_1_PWM = 11
MOTOR_2_PWM = 10
MOTOR_3_PWM = 9

MOTOR_1_A = 5
MOTOR_2_A = 7
MOTOR_3_A = 6

MOTOR_1_B = 8
MOTOR_2_B = 4
MOTOR_3_B = 3

R9 = 4670
R10 = 1940

TEMPERATURE_PIN = 0
VOLTAGE_PIN = 3


from time import sleep
import signal
from PyMata.pymata import PyMata
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

def cb_analog(args):
    global temp, voltage
    _, pin, value = args
    if pin == TEMPERATURE_PIN:
        temp = 5.0 * value * 100.0 / 1023
    elif pin == VOLTAGE_PIN:
        voltage = value * 5.0 / 1023 * (R9+R10) / R10
    print "Battery voltage: %.2f (V) Temperature: %.1f (C)" % (voltage, temp)

board.set_pin_mode(TEMPERATURE_PIN,  board.INPUT,  board.ANALOG, cb_analog)
board.set_pin_mode(VOLTAGE_PIN,  board.INPUT,  board.ANALOG, cb_analog)

def signal_handler(sig, frame):
    board.digital_write(MOTOR_1_B, 0)
    board.digital_write(MOTOR_1_A, 0)
    board.digital_write(MOTOR_2_B, 0)
    board.digital_write(MOTOR_2_A, 0)
    board.digital_write(MOTOR_3_B, 0)
    board.digital_write(MOTOR_3_A, 0)

    board.analog_write(MOTOR_1_PWM, 255)
    board.analog_write(MOTOR_2_PWM, 255)
    board.analog_write(MOTOR_3_PWM, 255)
    exit(signal.SIGKILL)

signal.signal(signal.SIGINT, signal_handler)


from math import sin
while True:
    speed = int(sin(time()/8) * 255)
    print(255-abs(speed))

    board.analog_write(MOTOR_1_PWM, 255)
    board.digital_write(MOTOR_1_A, 0)
    board.digital_write(MOTOR_1_B, 0)
    board.digital_write(MOTOR_1_A, speed < 0)
    board.digital_write(MOTOR_1_B, speed > 0)
    board.analog_write(MOTOR_1_PWM, 255-abs(speed))


    board.analog_write(MOTOR_2_PWM, 255)
    board.digital_write(MOTOR_2_A, 0)
    board.digital_write(MOTOR_2_B, 0)
    board.digital_write(MOTOR_2_A, speed < 0)
    board.digital_write(MOTOR_2_B, speed > 0)
    board.analog_write(MOTOR_2_PWM, 255-abs(speed))

    board.analog_write(MOTOR_3_PWM, 255)
    board.digital_write(MOTOR_3_A, 0)
    board.digital_write(MOTOR_3_B, 0)
    board.digital_write(MOTOR_3_A, speed < 0)
    board.digital_write(MOTOR_3_B, speed > 0)
    board.analog_write(MOTOR_3_PWM, 255-abs(speed))

    sleep(0.2)

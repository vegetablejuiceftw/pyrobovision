import numpy
import serial
from threading import Thread
from time import sleep, time

from PyMata.pymata import PyMata
from math import cos, sin, radians, atan2, pi


class Sensor:
	TEMPERATURE_PIN = 0
	VOLTAGE_PIN = 3

	def __init__(self):
		self.temp, self.voltage = -1, -1

	def set_board(self, board):
		return
		board.set_pin_mode(self.TEMPERATURE_PIN,  board.INPUT,  board.ANALOG, self.sensor_handler)
		board.set_pin_mode(self.VOLTAGE_PIN,  board.INPUT,  board.ANALOG, self.sensor_handler)

	def sensor_handler(self, args):
		R9 = 4670
		R10 = 1940
		_, pin, value = args
		if pin == self.TEMPERATURE_PIN:
			self.temp = 5.0 * value * 100.0 / 1023
		elif pin == self.VOLTAGE_PIN:
			self.voltage = value * 5.0 / 1023 * (R9+R10) / R10

		print( "Battery voltage: %.2f (V) Temperature: %.1f (C)" % (self.voltage, self.temp))
		sleep(0.1)



class Motor(Thread):
	# Motor pins on Arduino
	MOTOR_1_PWM = 11
	MOTOR_2_PWM = 9
	MOTOR_3_PWM = 10

	MOTOR_1_A = 5
	MOTOR_2_A = 6
	MOTOR_3_A = 7

	MOTOR_1_B = 8
	MOTOR_2_B = 3
	MOTOR_3_B = 4

	KICKER = 14

	SENSORS = Sensor() # not implemented

	MODE_A = "A"
	MODE_B = "B"

	def __init__(self, *args, **kwargs):
		Thread.__init__(self)
		self.daemon = True
		self.running = False
		self.mock_mode = False
		self.board = None
		self.data = {}
		self.last_direction = None
		self.kicker_start = time() - 0.71  # no kick on start
		self.mode = Motor.MODE_A
		self.danger_start = None
		self.start()

	def get_kicker_status(self):
		REGEN_TIME = 4

		since = time() - self.kicker_start
		if self.make_kick() and since > REGEN_TIME:
			self.kicker_start = time()

		return (time() - self.kicker_start) < 0.7

	def load_data(self, data):
		if data.get("M_A"): 
			self.mode = Motor.MODE_A
			print("MOTOR IN MODE A")
		if data.get("M_B"): 
			self.mode = Motor.MODE_B
			self.danger_start = time()
			print("MOTOR IN MODE B, simulating for some time")

		if data.get("TYPE") != self.mode:
			return
		self.data.update(data)

	def handle_simulation(self):
		if self.danger_start and time() - self.danger_start > 2:
			print("MOTOR simulation over")
			self.mode = Motor.MODE_A
			self.danger_start = None
			self.load_data({"Fx": 0, "Fy": 0, "Fw":0, "TYPE": Motor.MODE_A})

	def setup_pymata(self):
		# Here we initialize the motor pins on Arduino
		try:
			for k, v in [
				("MOTOR_1_PWM", self.MOTOR_1_PWM),
				("MOTOR_2_PWM", self.MOTOR_2_PWM),
				("MOTOR_3_PWM", self.MOTOR_3_PWM),
				("MOTOR_1_A", self.MOTOR_1_A),
				("MOTOR_2_A", self.MOTOR_2_A),
				("MOTOR_3_A", self.MOTOR_3_A),
				("MOTOR_1_B", self.MOTOR_1_B),
				("MOTOR_2_B", self.MOTOR_2_B),
				("MOTOR_3_B", self.MOTOR_3_B),
			]:
				print(k, v)

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

			board.set_pin_mode(self.KICKER,   board.OUTPUT, board.DIGITAL)			

			board.digital_write(self.KICKER, False)

			self.SENSORS.set_board(board)

			self.board = board
			self.running = True

		except (serial.serialutil.SerialException, FileNotFoundError) as err:
			print("# Something wrong with the serial device:{}".format(err))
			print("# Running in MOCK mode")
			self.mock_mode = True

	def clean_up(self):
		if self.board:
			# self.board.reset() # does weird shit
			# so we do manual labor
			self.board.digital_write(self.MOTOR_1_B, False)
			self.board.digital_write(self.MOTOR_1_A, False)
			self.board.digital_write(self.MOTOR_2_B, False)
			self.board.digital_write(self.MOTOR_2_A, False)
			self.board.digital_write(self.MOTOR_3_B, False)
			self.board.digital_write(self.MOTOR_3_A, False)

			self.board.analog_write(self.MOTOR_1_PWM, 255)
			self.board.analog_write(self.MOTOR_2_PWM, 255)
			self.board.analog_write(self.MOTOR_3_PWM, 255)

			self.board.digital_write(self.KICKER, True)  # should close with discharge

		self.running = False
		self.mock_mode = False

	def __del__(self):
		print("# DELETING MOTOR")
		self.clean_up()

	def close(self):
		self.clean_up()
		print("# Motor closed")

	def get_xyw(self):
		Fx, Fy, Fw = -self.data.get('Fx', 0), self.data.get('Fy', 0), self.data.get('Fw', 0)
		Fx, Fy, Fw = Fx * 0.99, Fy * 0.99, Fw * 0.99
		return Fx, Fy, Fw

	def make_kick(self):
		return self.data.get('K')

	def translate(self):
		Fx, Fy, Fw = self.get_xyw()

		backwards_matrix = [[-1/2,-1/2,1],[3**0.5/2,-3**0.5/2,0],[1,1,1]]
		# backwards_matrix = [[-1/2,-1/2,1],[3**0.5/2,-3**0.5/2,0],[1/3,1/3,1/3]]

		matrix = numpy.linalg.inv(backwards_matrix)

		Fa, Fb, Fc = numpy.dot(matrix, [Fx, Fy, Fw])

		return Fa, Fb, Fc

	def run(self):
		print("# START MOTOR THREAD")
		self.setup_pymata()
		print("# LOADED PYMATA 2")

		last = ()
		while self.mock_mode:
			Fa, Fb, Fc = self.translate()
			if self.last_direction != (Fa, Fb, Fc):
				# print("INPUT:  {:.4f} {:.4f} {:.4f}".format(*self.get_xyw()))
				print("RESULT: {:.4f} {:.4f} {:.4f}".format(Fa, Fb, Fc))
			self.last_direction = (Fa, Fb, Fc)
			sleep(0.02)

		while self.running:
			sleep(0.008)
			self.handle_simulation()

			#print(self.get_kicker_status(), time() - self.kicker_start)
			self.board.digital_write(self.KICKER, self.get_kicker_status())

			Fa, Fb, Fc = self.translate()
			if self.last_direction == (Fa, Fb, Fc):
				continue
			self.last_direction = (Fa, Fb, Fc)
			#print("RESULT: {:.4f} {:.4f} {:.4f}".format(Fa, Fb, Fc))

			# reset things TODO: wai thou?
			self.board.analog_write(self.MOTOR_1_PWM, 255)
			self.board.analog_write(self.MOTOR_2_PWM, 255)
			self.board.analog_write(self.MOTOR_3_PWM, 255)

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
			dFa, dFb, dFc = abs(int(float(Fa) * 255)), abs(int(float(Fb) * 255)), abs(int(float(Fc) * 255))
			# print(dFa,dFb,dFc)

			self.board.analog_write(self.MOTOR_1_PWM, 255 - dFa)
			self.board.analog_write(self.MOTOR_2_PWM, 255 - dFb)
			self.board.analog_write(self.MOTOR_3_PWM, 255 - dFc)

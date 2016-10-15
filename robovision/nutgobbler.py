from math import cos, sin

import numpy
from threading import Thread
from time import sleep

# http://southpark.wikia.com/wiki/Nut_Gobbler
class BallSucker(Thread):
	def __init__(self, motion_driver):
		self.map = {} # rotation: [(itensity,x-coord)]
		self.fov = 3 / 4 * 75 / 2 # 90 degrees rotated fov drift when scaled -1 to 1
		self.motion_driver = motion_driver

		Thread.__init__(self)
		self.daemon = True
		self.running = False
		self.start()

	@property
	def rotation(self):
		return self.motion_driver.rotation

	def update_camera(self, id, data):
		self.map[id] = data
		
	def itensity(self):
		tuples = []
		for k,v in self.map.items():
			for d, r in v:
				tuples.append((d, k + r * self.fov))
		return sorted(tuples)   

	def where_do_i_go(self):
		ordered_options = self.itensity()
		intensity, rotation = ordered_options[0]

		Fx, Fy, Fw = cos(rotation), sin(rotation), 0

		self.motion_driver.load_data({"Fx": Fx, "Fy": Fy})

	def run(self):
		while self.running:
			sleep(0.1)

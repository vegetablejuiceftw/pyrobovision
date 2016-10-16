from math import cos, sin

import numpy
from threading import Thread
from time import sleep

# http://southpark.wikia.com/wiki/Nut_Gobbler
class BrainFuck(Thread):
	def __init__(self, motion_driver):
		self.map = {} # rotation: [(itensity,x-coord)]
		self.fov = 3 / 4 * 75 / 2 # 90 degrees rotated fov drift when scaled -1 to 1
		self.motion_driver = motion_driver

		Thread.__init__(self)
		self.daemon = True
		self.running = True
		self.start()

	@property
	def rotation(self): # MOCK
		return self.motion_driver.rotation

	def report(self, id, data):
		self.map[id] = data
		
	def itensity(self): # MOCK
		tuples = []
		for k,v in self.map.items():
			for d, r in v:
				tuples.append((d, k + r * self.fov))
		return sorted(tuples)   

	def where_do_i_go(self): # MOCK
		ordered_options = self.itensity()
		intensity, rotation = ordered_options[0]
		Fx, Fy, Fw = cos(rotation), sin(rotation), 0
		self.motion_driver.load_data({"Fx": Fx, "Fy": Fy})

	def run(self):
		while self.running:
			intensity, cx = self.map[0][0] if 0 in self.map else (-1, 0)
			# print("Brainfeck: {:.4f} {:.4f}".format(intensity, cx))
			if 0.005 > intensity or intensity > 0.25:
				self.motion_driver.load_data({"Fx": 0, "Fy": 0, "Fw":0, "TYPE":"B"})
			else:
				self.motion_driver.load_data({"Fx": cx / 3, "Fy": 0.2 + round(0.25-intensity,2), "Fw": round(cx/2.3,2), "TYPE":"B"})
			sleep(0.008)

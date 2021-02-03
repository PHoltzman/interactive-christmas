import sched
import threading
from datetime import datetime, timedelta

from Lights import Lights

class Interlude:
	def __init__(self, name, num_pixels, light_sender):
		self.name = name
		self.num_pixels = num_pixels
		self.light_sender = light_sender
		
		self.is_active = False
		self.last_motion_step_time = datetime.now()
		
		self.current_packet_plan = Lights.make_interlude_packet_plan(self.num_pixels)
		self.current_packet_plan_index = 0
		self.time_delay = 0.05
			
	def update_pixel_allocation(self, num_pixels):
		self.num_pixels = num_pixels
		self.run_lights()
	
	def run_lights(self):
		self.current_packet_plan = Lights.make_interlude_packet_plan(self.num_pixels)
		self.current_packet_plan_index = 0
		self.last_motion_step_time = datetime.now()
				
		# invoke light updater
		self.light_sender.set_lights(self.name, self.current_packet_plan[self.current_packet_plan_index])
		
	def next_moving_step(self, current_time):
		if (current_time - self.last_motion_step_time).total_seconds() >= self.time_delay:
			# shift the sequence
			if self.current_packet_plan_index == len(self.current_packet_plan) - 1:
				self.current_packet_plan_index = 0
			else:
				self.current_packet_plan_index += 1
			
			new_packet = self.current_packet_plan[self.current_packet_plan_index]
			self.last_motion_step_time = current_time
				
			# invoke light updater
			self.light_sender.set_lights(self.name, new_packet)
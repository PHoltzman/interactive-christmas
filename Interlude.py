import sched
import threading
from datetime import datetime, timedelta

from BaseController import PacketPlan
from Lights import Lights

class Interlude:
	def __init__(self, logger, name, light_dimensions, light_sender):
		self.logger = logger
		self.name = name
		self.light_dimensions = light_dimensions
		self.light_sender = light_sender
		
		self.is_active = False
		
		self.main_packet_plan = self.make_main_packet_plan()
		
	def make_main_packet_plan(self):
		return PacketPlan(
			Lights.make_interlude_packet_time_series(self.light_dimensions),
			is_repeating=True,
			time_delay=0.25
		)
			
	def update_pixel_allocation(self, light_dimensions, **kwargs):
		self.light_dimensions = light_dimensions
		self.main_packet_plan = self.make_main_packet_plan()
		self.light_sender.set_lights(self.name, self.main_packet_plan.get_current_packet())
	
	def next_moving_step(self, current_time):
		is_advanced, is_ended = self.main_packet_plan.advance_packet_plan(current_time)
		if is_advanced:	
			# invoke light updater
			self.light_sender.set_lights(self.name, self.main_packet_plan.get_current_packet())
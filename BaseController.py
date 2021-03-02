import threading
from datetime import datetime, timedelta


class PacketPlan:
	def __init__(self, packet_plan=None, current_index=0, is_repeating=False, time_delay=1.0):
		self.packet_plan = packet_plan if packet_plan is not None else []
		self.current_index = current_index
		self.is_repeating = is_repeating
		self.time_delay = time_delay
		self.last_motion_step_time = datetime.now()
		
	def get_current_packet(self):
		try:
			return self.packet_plan[self.current_index]
		except IndexError:
			return []
		
	def advance_packet_plan(self, current_time):
		is_ended = False
		is_advanced = False
		if (current_time - self.last_motion_step_time).total_seconds() >= self.time_delay:
			is_advanced = True
		
			if self.is_repeating:
				if self.current_index == len(self.packet_plan) - 1:
					self.current_index = 0
				else:
					self.current_index += 1
					
			else:
				if self.current_index == len(self.packet_plan) - 1:
					is_ended = True
				else:
					self.current_index += 1
				
			self.last_motion_step_time = current_time
			
		return is_advanced, is_ended

class BaseController:
	def __init__(self, controller, name, light_dimensions, light_sender):
		self.controller = controller
		self.name = name
		self.light_dimensions = light_dimensions
		self.light_sender = light_sender
		
		self.last_input_datetime = datetime.now() - timedelta(hours=1)  # initialize to a long time ago so controller starts as inactive
		self.last_motion_step_time = self.last_input_datetime
		self.is_active = False
		
		# start a thread to check periodically on the last input datetime and determine if the controller has gone inactive
		self.check_for_inactivity()
		
		for button in controller.buttons:
			button.when_pressed = self.on_button_pressed
			button.when_released = self.on_button_released
			
		for axis in controller.axes:
			axis.when_moved = self.on_axis_moved
			
	def on_button_pressed(self, button):
		self.register_input()
	
	def on_button_released(self, button):
		self.register_input()
		
	def on_axis_moved(self, axis):
		self.register_input()
		
	def register_input(self):
		self.last_input_datetime = datetime.now()
		if not self.is_active:
			self.is_active = True
			self.light_sender.go_active(self.name)
			
	def update_pixel_allocation(self, light_dimensions):
		raise NotImplementedError
		# self.light_dimensions = light_dimensions
		# self.run_lights(self.current_motion_colors, self.select_mode)
		
	def check_for_inactivity(self):
		raise NotImplementedError
		# if self.is_active:
			# if (datetime.now() - self.last_input_datetime).total_seconds() > 10:
				# # this controller is now inactive so do stuff accordingly
				# self.is_active = False
				# self.current_colors = self.current_motion_colors = []
								
				# # tell the rest of the system that they can release our pixels
				# self.light_sender.go_inactive(self.name)
			
		# t = threading.Timer(5, self.check_for_inactivity).start()
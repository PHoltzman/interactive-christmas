import threading
from datetime import datetime, timedelta

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
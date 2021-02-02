import sched
import threading
from datetime import datetime, timedelta

from Lights import Lights

class Guitar:
	def __init__(self, controller, name, num_pixels, light_sender):
		self.controller = controller
		self.name = name
		self.num_pixels = num_pixels
		self.light_sender = light_sender
		
		self.last_input_datetime = datetime.now() - timedelta(hours=1)  # initialize to a long time ago so controller starts as inactive
		self.is_active = False
		
		# start a thread to check periodically on the last input datetime and determine if the controller has gone inactive
		self.check_for_inactivity()
		
		self.current_mode = 0
		self.select_mode = 0
		self.selector_position = None
		self.last_motion_step_time = None
		self.dim_ratio = None
		
		self.current_colors = []
		self.current_packet_plan = [Lights.make_whole_string_packet(0, 0, 0, self.num_pixels)]
		self.current_packet_plan_index = 0
		
		for button in controller.buttons:
			button.when_pressed = self.on_button_pressed
			button.when_released = self.on_button_released
			
		for axis in controller.axes:
			if self.get_friendly_axis_name(axis.name) == 'selector':
				# initialize selector switch
				_, self.selector_position = self.get_axis_details(axis)
				self.time_delay = self.get_time_delay_from_selector_position(self.selector_position)
			axis.when_moved = self.on_axis_moved
			
	def update_pixel_allocation(self, num_pixels):
		self.num_pixels = num_pixels
		self.run_lights(self.current_colors, self.select_mode)
			
	def check_for_inactivity(self):
		if self.is_active:
			if (datetime.now() - self.last_input_datetime).total_seconds() > 30:
				# this controller is now inactive so do stuff accordingly
				self.is_active = False
								
				# tell the rest of the system that they can release our pixels
				self.light_sender.go_inactive(self.name)
			
		t = threading.Timer(5, self.check_for_inactivity).start()
	
	def register_input(self):
		self.last_input_datetime = datetime.now()
		if not self.is_active:
			self.is_active = True
			self.light_sender.go_active(self.name)
	
	def on_button_pressed(self, button):
		self.register_input()
		color = self.get_friendly_button_name(button)
		if color not in self.current_colors:
			self.current_colors.append(color)
		print(color, 'press')
		
	def on_button_released(self, button):
		self.register_input()
		color = self.get_friendly_button_name(button)
		if color in self.current_colors:
			self.current_colors.remove(color)
		print(color, 'release')
		
		if color == 'select':
			# set the select mode if necessary
			self.select_mode = 0 if self.select_mode == 5 else self.select_mode + 1
			print(f'SELECT_MODE = {self.select_mode}')
			
	def on_axis_moved(self, axis):
		self.register_input()
		device, value = self.get_axis_details(axis)
		
		if device == 'dpad' and value in ['up', 'down']:
			self.run_lights(self.current_colors, mode=self.select_mode)
			
		elif device == 'whammy':
			dimming_ratio = self.calculate_whammy_dimming(value)
			self.dim_ratio = None if dimming_ratio == 1 else dimming_ratio
			
			new_packet = self.dim_packet(self.current_packet_plan[self.current_packet_plan_index], self.dim_ratio)
						
			# invoke light updater
			self.light_sender.set_lights(self.name, new_packet)
				
		elif device == 'selector':
			self.selector_position = value
			self.time_delay = self.get_time_delay_from_selector_position(self.selector_position)
			print(f'Selector Position = {value}')
	
	
	def run_lights(self, color_list, mode=0):
		num_colors = len(color_list)
		if num_colors == 0:
			packet_plan = [Lights.make_whole_string_packet(0, 0, 0, self.num_pixels)]
			
		else:
			colors_rgb = [Lights.rgb_from_color(x) for x in color_list]
			if mode == 0:
				# lights alternate statically with each color that was pressed pixel by pixel
				packet_plan = [Lights.get_alternating_packet(colors_rgb, self.num_pixels)]
				
			elif mode == 1:
				# lights form 1 block of each color that was pressed
				packet_plan = [Lights.get_blocks_packet(colors_rgb, self.num_pixels)]
			
			else:  # moving modes
				packet_plan = []
				if mode == 2:
					# the lights in the string scroll perpetually in the same pattern as mode 0
					packet = Lights.get_alternating_packet(colors_rgb, self.num_pixels)
					for i in range(len(colors_rgb)):
						packet_plan.append(Lights.shift_packet(packet, i, 'right'))
					
				elif mode == 3:
					# the lights in the string scroll perpetually in the same pattern as mode 1
					packet = Lights.get_blocks_packet(colors_rgb, self.num_pixels)
					for i in range(self.num_pixels):
						packet_plan.append(Lights.shift_packet(packet, i, 'right'))
					
				elif mode == 4:
					# the lights wipe on and off, alternating like in mode 0
					packet = Lights.get_alternating_packet(colors_rgb, self.num_pixels)
					for i in range(self.num_pixels):
						packet_plan.append(Lights.sub_packet(packet, i))
					
					for i in range(self.num_pixels -1, 0, -1):
						packet_plan.append(Lights.sub_packet(packet, i))
						
				elif mode == 5:
					# the lights wipe on and off, in color blocks like in mode 1
					packet = Lights.get_blocks_packet(colors_rgb, self.num_pixels)
					for i in range(self.num_pixels):
						packet_plan.append(Lights.sub_packet(packet, i))
					
					for i in range(self.num_pixels -1, 0, -1):
						packet_plan.append(Lights.sub_packet(packet, i))
					
				self.last_motion_step_time = datetime.now()
		
		self.current_packet_plan = packet_plan
		self.current_packet_plan_index = 0
		
		self.current_mode = mode
		
		# check whammy position and dim accordingly
		new_packet = self.dim_packet(self.current_packet_plan[self.current_packet_plan_index], self.dim_ratio)
			
		# invoke light updater
		self.light_sender.set_lights(self.name, new_packet)
		
	def next_moving_step(self, current_time):
		if self.current_mode > 1 and (current_time - self.last_motion_step_time).total_seconds() >= self.time_delay:
			# shift the sequence
			if self.current_packet_plan_index == len(self.current_packet_plan) - 1:
				self.current_packet_plan_index = 0
			else:
				self.current_packet_plan_index += 1
			
			# check whammy position and dim accordingly
			new_packet = self.dim_packet(self.current_packet_plan[self.current_packet_plan_index], self.dim_ratio)
				
			self.last_motion_step_time = current_time
				
			# invoke light updater
			self.light_sender.set_lights(self.name, new_packet)

	@staticmethod
	def dim_packet(packet, dim_ratio):
		if dim_ratio is not None:
			new_packet = [int(x * dim_ratio) for x in packet]
		else:
			new_packet = packet
			
		return new_packet
		
	@staticmethod
	def calculate_whammy_dimming(whammy_value):
		return (whammy_value + 1) / 2 * -.9 + 1 # make it fully positive and scale for 0 (untouched) to 1 (fully engaged)
		
	@staticmethod
	def get_friendly_button_name(button):
		button_mapping = {
			"button_a": "green",
			"button_b": "red",
			"button_x": "blue",
			"button_y": "yellow",
			"button_trigger_l": "orange",
			"button_select": "select",
			"button_start": "start",
			"button_mode": "mode",
			"button_thumb_l": "neck"
		}
		try:
			return button_mapping[button.name]
		except KeyError:
			return button.name
			
	@staticmethod
	def get_friendly_axis_name(axis_name):
		axis_mapping = {
			"hat": "dpad",
			"axis_r": "whammy",
			"trigger_l": "selector"
		}
		try:
			return axis_mapping[axis_name]
		except KeyError:
			return 'unknown'
	
	@staticmethod
	def get_axis_details(axis):
		hat_mapping = {
			(0, 1): "up",
			(1, 1): "right_up",
			(1, 0): "right",
			(1, -1): "right_down",
			(0, -1): "down",
			(-1, -1): "left_down",
			(-1, 0): "left",
			(-1, 1): "left_up"
		}
		friendly_name = Guitar.get_friendly_axis_name(axis.name)
		if friendly_name == 'dpad':
			value = hat_mapping[(axis.x, axis.y)]
		elif friendly_name == 'whammy':
			value = axis.x
		elif friendly_name == 'selector':
			value = Guitar.get_selector_value(axis.value)
		else:
			value = 'unknown'
			
		return friendly_name, value
	
	@staticmethod
	def get_selector_value(raw_value):
		val = round(raw_value, 1)
		if val == 0.1:
			return 1
		elif val == 0.3:
			return 2
		elif val == 0 or val == 0.7:
			return 3
		else:
			return 4
	
	@staticmethod
	def get_time_delay_from_selector_position(selector_value):
		if selector_value == 1:
			return 0.5
		elif selector_value == 2:
			return 0.3
		elif selector_value == 3:
			return 0.1
		else:
			return 0.05
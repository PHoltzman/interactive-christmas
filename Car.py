import threading
import random
from datetime import datetime, timedelta

from Lights import Lights


class Car:
	def __init__(self, controller, name, light_dimensions, light_sender):
		self.controller = controller
		self.name = name
		self.light_dimensions = light_dimensions
		self.light_sender = light_sender
		
		self.last_input_datetime = datetime.now() - timedelta(hours=1)  # initialize to a long time ago so controller starts as inactive
		self.is_active = False
		
		# start a thread to check periodically on the last input datetime and determine if the controller has gone inactive
		self.check_for_inactivity()
		
		self.select_mode = 0
		self.segment_size = 1
		self.dim_ratio = 0
		self.current_wheel_value = 0
		self.direction, self.time_delay = self.calculate_wheel_time_delay(self.current_wheel_value)
		self.last_motion_step_time = datetime.now()
		
		self.current_colors = ['red', 'green']
		self.current_packet_plan = [[[[]]]]
		self.current_packet_plan_index = 0
		
		for button in controller.buttons:
			button.when_pressed = self.on_button_pressed
			button.when_released = self.on_button_released
			
		for axis in controller.axes:
			axis.when_moved = self.on_axis_moved
			
	def update_pixel_allocation(self, light_dimensions):
		self.light_dimensions = light_dimensions
		L, H, D = light_dimensions
		if L == 0 or H == 0 or D == 0:
			self.current_packet_plan = [[[[]]]]
		else:
			self.current_packet_plan = self.make_packet_plan()
		self.current_packet_plan_index = 0
		self.update_lights()
			
	def check_for_inactivity(self):
		if self.is_active:
			if (datetime.now() - self.last_input_datetime).total_seconds() > 10:
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
		print(color, 'press')
		
	def on_button_released(self, button):
		self.register_input()
		
		color = self.get_friendly_button_name(button)
		print(color, 'release')
		
		packet_plan = []
		if color == 'up_left':
			# change the mode between alternating and blocks
			self.select_mode = 0 if self.select_mode == 1 else self.select_mode + 1
			print(f'SELECT_MODE = {self.select_mode}')
			
			self.current_packet_plan = self.make_packet_plan()
			self.current_packet_plan_index = 0
			self.update_lights()
			
		elif color == 'up_right':
			# change the colors and number of colors randomly
			num_colors = random.randint(2,4)
			color_list = random.sample(Lights.COLOR_LIST, num_colors)
			random.shuffle(color_list)
			self.current_colors = color_list
			
			self.current_packet_plan = self.make_packet_plan()
			self.current_packet_plan_index = 0
			self.update_lights()
			
		elif color == 'down_left':
			# set the segment_size. This is used to control the size of segments for the alternating mode. Also have to regenerate the current_packet_base 
			self.segment_size = 1 if self.segment_size == 4	 else self.segment_size + 1
			print(f'segment_size = {self.segment_size}')

			self.current_packet_plan = self.make_packet_plan()
			self.current_packet_plan_index = 0
			self.update_lights()
			
	def make_packet_plan(self):
		L, H, D = self.light_dimensions
		packet_plan = []
		colors_rgb = [Lights.rgb_from_color(x) for x in self.current_colors]
		if self.select_mode == 0:
			# alternating
			packet = Lights.get_alternating_packet(colors_rgb, self.light_dimensions, self.segment_size)
			for i in range(len(colors_rgb)):
				for j in range(self.segment_size):
					packet_plan.append(Lights.shift_packet(packet, i * self.segment_size + j + 1, right=True))
					
		elif self.select_mode == 1:
			# blocks
			packet = Lights.get_blocks_packet(colors_rgb, self.light_dimensions)
			for i in range(L):
				packet_plan.append(Lights.shift_packet(packet, i, right=True))
				
		return packet_plan

	def on_axis_moved(self, axis):
		self.register_input()
		device, value, value2 = self.get_axis_details(axis)
			
		if device == 'gas_wheel':
			# process gas pedal dimming
			self.dim_ratio = self.calculate_gas_dimming(value)			
			self.update_lights()
			
			# process steering wheel horizontal motion
			if value2 is not None:
				value2 = round(value2, 1)
				
			if value2 != self.current_wheel_value:
				# this means the wheel has moved so we need to process it
				self.current_wheel_value = value2
				self.direction, self.time_delay = self.calculate_wheel_time_delay(value2)
				# print(f'direction={self.direction}, time_delay={self.time_delay}')
		
		else:
			print(f'{device} {value} {value2}')
			
	def update_lights(self):
		# apply the current dimming ratio
		new_packet = []
		for grid in self.current_packet_plan[self.current_packet_plan_index]:
			new_grid = []
			for row in grid:
				new_grid.append([(int(x[0] * self.dim_ratio), int(x[1] * self.dim_ratio), int(x[2] * self.dim_ratio)) for x in row])
			new_packet.append(new_grid)
				
		# invoke light updater
		self.light_sender.set_lights(self.name, new_packet)
		
	def next_moving_step(self, current_time):
		# determine when a sequence should be shifted
		if self.direction is not None and (current_time - self.last_motion_step_time).total_seconds() >= self.time_delay:
			# if direction is not None, that means the wheel is currently turned either left or right so we want motion
			# if the current_time is greater than the last motion time by at least the time_delay amount, then we need to do a motion step
			
			# shift the sequence
			if self.direction == 'right':
				if self.current_packet_plan_index == len(self.current_packet_plan) - 1:
					self.current_packet_plan_index = 0
				else:
					self.current_packet_plan_index += 1
			else:
				if self.current_packet_plan_index == 0:
					self.current_packet_plan_index = len(self.current_packet_plan) - 1
				else:
					self.current_packet_plan_index -= 1
			
			self.last_motion_step_time = current_time
			
		self.update_lights()
	
	@staticmethod
	def get_axis_details(axis):
		friendly_name = Car.get_friendly_axis_name(axis.name)
		if friendly_name == 'gas_wheel':
			gas_value = axis.y  # gas pedal: 1.0 untouched, -1.0 fully depressed
			wheel_value = axis.x  # steering wheel: -1.0 full left, 1.0 full right
			return friendly_name, gas_value, wheel_value
			
		elif friendly_name == 'brake':
			value = axis.value
			# 0.0 untouched, 1.0 fully depressed
		else:
			value = 'unknown'
			
		return friendly_name, value, None
		
	@staticmethod
	def get_friendly_axis_name(axis_name):
		axis_mapping = {
			"axis_l": "gas_wheel",
			"trigger_l": "brake"
		}
		try:
			return axis_mapping[axis_name]
		except KeyError:
			return axis_name
			
	@staticmethod
	def get_friendly_button_name(button):
		button_mapping = {
			"button_x": "up_left",
			"button_y": "up_right",
			"button_trigger_l": "down_left",
			"button_trigger_r": "down_right"
		}
		try:
			return button_mapping[button.name]
		except KeyError:
			return button.name
		
	@staticmethod
	def calculate_gas_dimming(gas_value):
		return (gas_value + 1) / 2 * -1 + 1 # make it fully positive and scale for 0 (untouched) to 1 (fully engaged)
		
	@staticmethod
	def calculate_wheel_time_delay(wheel_value):
		# scroll really fast at the limits. Don't scroll at all in the middle.
		# 50ms at limits. once per half second just next to center
		x = abs(wheel_value)
		if x < 0.2:
			# consider the wheel centered so stop any motion
			return None, None
		else:
			direction = 'right' if wheel_value > 0 else 'left'
			a = .1
			delay = a*x*x - 1.2*a*x - 0.5625*x + 0.2*a + 0.6125 
			return direction, delay
			
			
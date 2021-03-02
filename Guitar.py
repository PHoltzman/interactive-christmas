import threading
from datetime import datetime, timedelta

from BaseController import BaseController, PacketPlan
from Lights import Lights

class Guitar(BaseController):
	def __init__(self, controller, name, light_dimensions, light_sender):
		super().__init__(controller, name, light_dimensions, light_sender)
		
		self.current_mode = 0
		self.select_mode = 0
		self.selector_position = None
		self.dim_ratio = None
		
		self.motion_direction_list = ['right', 'down_right', 'down', 'down_left', 'left', 'up_left', 'up', 'up_right']
		self.motion_direction_index = 0
		
		self.current_colors = []
		self.current_motion_colors = []
		self.main_packet_plan = PacketPlan([Lights.make_whole_string_packet((0, 0, 0), self.light_dimensions)])
		
		for button in controller.buttons:
			button.when_pressed = self.on_button_pressed
			button.when_released = self.on_button_released
			
		for axis in controller.axes:
			if self.get_friendly_axis_name(axis.name) == 'selector':
				# initialize selector switch
				_, self.selector_position = self.get_axis_details(axis)
				self.main_packet_plan.time_delay = self.get_time_delay_from_selector_position(self.selector_position)
			axis.when_moved = self.on_axis_moved
			
	def update_pixel_allocation(self, light_dimensions):
		self.light_dimensions = light_dimensions
		self.run_lights(self.current_motion_colors, self.select_mode)
			
	def check_for_inactivity(self):
		if self.is_active:
			if (datetime.now() - self.last_input_datetime).total_seconds() > 10:
				# this controller is now inactive so do stuff accordingly
				self.is_active = False
				self.current_colors = self.current_motion_colors = []
								
				# tell the rest of the system that they can release our pixels
				self.light_sender.go_inactive(self.name)
			
		t = threading.Timer(5, self.check_for_inactivity).start()
	
	def on_button_pressed(self, button):
		super().on_button_pressed(button)
		color = self.get_friendly_button_name(button)
		if color not in self.current_colors:
			self.current_colors.append(color)
		print(color, 'press')
		
	def on_button_released(self, button):
		super().on_button_released(button)
		color = self.get_friendly_button_name(button)
		if color in self.current_colors:
			self.current_colors.remove(color)
		print(color, 'release')
		
		if color == 'select':
			# set the select mode if necessary
			self.select_mode = 0 if self.select_mode == 5 else self.select_mode + 1
			print(f'SELECT_MODE = {self.select_mode}')
			self.run_lights(self.current_motion_colors, mode=self.select_mode)
			
	def on_axis_moved(self, axis):
		super().on_axis_moved(axis)
		device, value = self.get_axis_details(axis)
		
		if device == 'dpad' and value in ['up', 'down']:
			self.current_motion_colors = list(self.current_colors)
			self.run_lights(self.current_colors, mode=self.select_mode)
			
		elif device == 'dpad' and value in ['left']:
			if self.motion_direction_index == 0:
				self.motion_direction_index = 7
			else:
				self.motion_direction_index -= 1
			print('Current motion direction = ' + self.motion_direction_list[self.motion_direction_index])
			self.run_lights(self.current_motion_colors, mode=self.select_mode)
		
		elif device == 'dpad' and value in ['right']:
			if self.motion_direction_index == 7:
				self.motion_direction_index = 0
			else:
				self.motion_direction_index += 1
			print('Current motion direction = ' + self.motion_direction_list[self.motion_direction_index])
			self.run_lights(self.current_motion_colors, mode=self.select_mode)
			
		elif device == 'whammy':
			dimming_ratio = self.calculate_whammy_dimming(value)
			self.dim_ratio = None if dimming_ratio == 1 else dimming_ratio
			
			new_packet = self.dim_packet(self.main_packet_plan.get_current_packet(), self.dim_ratio)
						
			# invoke light updater
			self.light_sender.set_lights(self.name, new_packet)
				
		elif device == 'selector':
			self.selector_position = value
			self.main_packet_plan.time_delay = self.get_time_delay_from_selector_position(self.selector_position)
			print(f'Selector Position = {value}')
	
	
	def run_lights(self, color_list, mode=0):
		L, H, D = self.light_dimensions
		num_colors = len(color_list)
		if num_colors == 0:
			packet_plan = PacketPlan([Lights.make_whole_string_packet((0, 0, 0), self.light_dimensions)])
			
		else:
			colors_rgb = [Lights.rgb_from_color(x) for x in color_list]
			if mode == 0:
				# lights alternate statically with each color that was pressed pixel by pixel
				packet_plan = PacketPlan([Lights.get_alternating_packet(colors_rgb, self.light_dimensions)])
				
			elif mode == 1:
				# lights form 1 block of each color that was pressed
				packet_plan = PacketPlan([Lights.get_blocks_packet(colors_rgb, self.light_dimensions)])
			
			else:  # moving modes
				packets = []
				motion_dirs = self.motion_direction_list[self.motion_direction_index].split('_')
				dir_kw_args = {x: True for x in motion_dirs}
				if mode == 2:
					# the lights in the string scroll perpetually in the same pattern as mode 0
					packet = Lights.get_alternating_packet(colors_rgb, self.light_dimensions)
					for i in range(len(colors_rgb)):
						packets.append(Lights.shift_packet(packet, i, **dir_kw_args))
					
				elif mode == 3:
					# the lights in the string scroll perpetually in the same pattern as mode 1
					packet = Lights.get_blocks_packet(colors_rgb, self.light_dimensions)
					for i in range(L):
						packets.append(Lights.shift_packet(packet, i, **dir_kw_args))
					
				elif mode == 4:
					# the lights wipe on and off, alternating like in mode 0
					packet = Lights.get_alternating_packet(colors_rgb, self.light_dimensions)
					for i in range(L+1):
						packets.append(Lights.sub_packet(packet, i))
					
					for i in range(L-1, 0, -1):
						packets.append(Lights.sub_packet(packet, i))
						
				elif mode == 5:
					# the lights wipe on and off, in color blocks like in mode 1
					packet = Lights.get_blocks_packet(colors_rgb, self.light_dimensions)
					for i in range(L+1):
						packets.append(Lights.sub_packet(packet, i))
					
					for i in range(L-1, 0, -1):
						packets.append(Lights.sub_packet(packet, i))
				
				packet_plan = PacketPlan(packets, is_repeating=True, time_delay=self.get_time_delay_from_selector_position(self.selector_position))
			
		self.main_packet_plan = packet_plan
		self.current_mode = mode
		
		# check whammy position and dim accordingly
		new_packet = self.dim_packet(self.main_packet_plan.get_current_packet(), self.dim_ratio)
			
		# invoke light updater
		self.light_sender.set_lights(self.name, new_packet)
		
	def next_moving_step(self, current_time):
		if self.current_mode > 1:
			is_advanced, is_ended = self.main_packet_plan.advance_packet_plan(current_time)
		
			if is_advanced:
				# check whammy position and dim accordingly
				new_packet = self.dim_packet(self.main_packet_plan.get_current_packet(), self.dim_ratio)
									
				# invoke light updater
				self.light_sender.set_lights(self.name, new_packet)

	@staticmethod
	def dim_packet(packet, dim_ratio):
		if dim_ratio is not None:
			new_packet = []
			for grid in packet:
				new_grid = []
				for row in grid:
					new_grid.append([(int(x[0] * dim_ratio), int(x[1] * dim_ratio), int(x[2] * dim_ratio)) for x in row])
				new_packet.append(new_grid)
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
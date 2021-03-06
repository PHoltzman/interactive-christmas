import threading
import random
from datetime import datetime, timedelta

from BaseController import BaseController, PacketPlan
from Lights import Lights


class Car(BaseController):
	def __init__(self, controller, name, light_dimensions, light_sender):
		super().__init__(controller, name, light_dimensions, light_sender)
		
		self.macro_mode = 0
		self.select_mode = 0
		self.segment_size = 1
		self.dim_ratio = 0
		self.current_wheel_value = 0
		self.current_gas_value = 0
		self.current_brake_value = 0
		
		self.is_reverse_mode = False
		self.is_reverse_mode_changed = False
		self.wheel_direction, self.wheel_time_delay = self.calculate_wheel_time_delay(self.current_wheel_value)
		self.gas_direction, self.gas_time_delay = self.calculate_gas_time_delay(self.current_gas_value)
		
		self.last_motion_step_time_wheel = self.last_input_datetime
		self.last_motion_step_time_gas = self.last_input_datetime

		self.current_colors = ['red', 'green']
		self.main_packet_plan = PacketPlan()
		self.temp_packet_plans = []
		
		# used for macro_mode 1
		self.target_pixel = None
		self.chase_pixel = None
		self.walls = []
		
		print(f'Macro Mode = {self.macro_mode}')
			
	def update_pixel_allocation(self, light_dimensions):
		self.light_dimensions = light_dimensions
		L, H, D = light_dimensions
		if L == 0 or H == 0 or D == 0:
			self.main_packet_plan = PacketPlan()
			self.temp_packet_plans = []
		else:
			self.main_packet_plan = self.make_packet_plan()
		self.chase_pixel = 0, 0, 0
		self.update_lights()
			
	def check_for_inactivity(self):
		if self.is_active:
			if (datetime.now() - self.last_input_datetime).total_seconds() > 10:
				# this controller is now inactive so do stuff accordingly
				self.is_active = False
								
				# tell the rest of the system that they can release our pixels
				self.light_sender.go_inactive(self.name)
			
		t = threading.Timer(5, self.check_for_inactivity).start()
	
	def on_button_pressed(self, button):
		super().on_button_pressed(button)
		color = self.get_friendly_button_name(button)
		if color == 'up_left':
			if not self.is_reverse_mode:
				self.is_reverse_mode = True
				self.is_reverse_mode_changed = True
	
	def on_button_released(self, button):
		super().on_button_released(button)
		
		color = self.get_friendly_button_name(button)
		print(color, 'release')
		
		packet_plan = []
		if color == 'up_left':
			# for macro_mode 0, make the gas and brake pedal cause reverse directions
			if self.is_reverse_mode:
				self.is_reverse_mode = False
				self.is_reverse_mode_changed = True
			
		elif color == 'up_right':
			# change the colors and number of colors randomly
			num_colors = random.randint(2,4)
			color_list = random.sample(Lights.COLOR_LIST, num_colors)
			random.shuffle(color_list)
			self.current_colors = color_list
			
			self.main_packet_plan = self.make_packet_plan()
			self.update_lights()
			
		elif color == 'down_left':
			# change the mode between alternating and blocks
			self.select_mode = 0 if self.select_mode == 1 else self.select_mode + 1
			print(f'SELECT_MODE = {self.select_mode}')
			
			self.main_packet_plan = self.make_packet_plan()
			self.update_lights()
			
			# # set the segment_size. This is used to control the size of segments for the alternating mode. Also have to regenerate the current_packet_base 
			# self.segment_size = 1 if self.segment_size == 4	 else self.segment_size + 1
			# print(f'segment_size = {self.segment_size}')

			# self.current_packet_plan = self.make_packet_plan()
			# self.current_packet_plan_index = 0
			# self.update_lights()
			
		elif color == 'down_right':
			# toggle macro modes between light control and the "chase the pixel" game
			# 0 = lights, 1 = game
			self.macro_mode = 0 if self.macro_mode == 1 else self.macro_mode + 1
			print(f'Macro Mode = {self.macro_mode}')			
			self.main_packet_plan = self.make_packet_plan()
			self.update_lights()
			
	def make_packet_plan(self):
		L, H, D = self.light_dimensions
		packets = []
		
		if self.macro_mode == 0:
			colors_rgb = [Lights.rgb_from_color(x) for x in self.current_colors]
			if self.select_mode == 0:
				# alternating
				packet = Lights.get_alternating_packet(colors_rgb, self.light_dimensions, self.segment_size)
				for i in range(len(colors_rgb)):
					for j in range(self.segment_size):
						packets.append(Lights.shift_packet(packet, i * self.segment_size + j + 1, right=True))
						
			elif self.select_mode == 1:
				# blocks
				packet = Lights.get_blocks_packet(colors_rgb, self.light_dimensions)
				for i in range(L):
					packets.append(Lights.shift_packet(packet, i, right=True))
		
		elif self.macro_mode == 1:
			self.chase_pixel = (0,0,0)
			self.make_game_board(chase_position=self.chase_pixel)
			packets.append(self.draw_game_board())
		
		return PacketPlan(packets)

	def on_axis_moved(self, axis):
		super().on_axis_moved(axis)
		device, value, value2 = self.get_axis_details(axis)
		L, H, D = self.light_dimensions
		
		if device == 'gas_wheel':
			is_changed = False
			normalized_gas_value = round((value + 1) / 2 * -1 + 1, 2)  # normalizes gas value to range of 0 (off) to 1 (on) with 2 decimal precision
			if normalized_gas_value != self.current_gas_value:
				# this means the pedal position has changed so we need to process it
				is_changed = True
				self.current_gas_value = normalized_gas_value
				self.gas_direction, self.gas_time_delay = self.calculate_gas_time_delay(normalized_gas_value)
			
			# process steering wheel horizontal motion
			if value2 is not None:
				normalized_wheel_value = round(value2, 1)
				if normalized_wheel_value != self.current_wheel_value:
					# this means the wheel has moved so we need to process it
					is_changed = True
					self.current_wheel_value = normalized_wheel_value
					self.wheel_direction, self.wheel_time_delay = self.calculate_wheel_time_delay(normalized_wheel_value)
			
			if is_changed:
				self.update_lights()
		
		else:
			print(f'{device} {value} {value2}')
			
	def update_lights(self):
		# invoke light updater
		new_packet = self.main_packet_plan.get_current_packet()
		if self.temp_packet_plans:
			packets_to_merge = [new_packet] + [x.get_current_packet() for x in self.temp_packet_plans]
			try:
				new_packet = Lights.merge_packets(packets_to_merge, self.light_dimensions)
			except IndexError:
				print('Index error when merging packets, likely due to light dimensions being reallocated. Skipping merge and using main packet instead and expecting it to fix itself next time around')
		
		self.light_sender.set_lights(self.name, new_packet)
		
	def next_moving_step(self, current_time):
		# determine when a sequence should be shifted
		right = False
		left = False
		up = False
		down = False
		changed = False
		
		# if direction is not None, that means the wheel/gas is engaged so we want motion
		# if the current_time is greater than the last motion time by at least the time_delay amount, then we need to do a motion step
		if self.wheel_direction is not None and (current_time - self.last_motion_step_time_wheel).total_seconds() >= self.wheel_time_delay:
			self.last_motion_step_time_wheel = current_time
			
			if self.wheel_direction == 'right':
				right = True
			else:
				left = True
			changed = True
			
		indexes_to_remove = []
		for i, packet_plan in enumerate(self.temp_packet_plans):
			is_advanced, is_ended = packet_plan.advance_packet_plan(current_time)
			if is_advanced:
				changed = True
			if is_ended:
				indexes_to_remove.append(i)
				
		indexes_to_remove.sort(reverse=True)
		for ind in indexes_to_remove:
			try:
				self.temp_packet_plans.pop(ind)
			except IndexError:
				pass
				
		if self.macro_mode == 0:
			if self.gas_direction is not None and ((current_time - self.last_motion_step_time_gas).total_seconds() >= self.gas_time_delay or self.is_reverse_mode_changed):
				self.last_motion_step_time_gas = current_time
				if self.is_reverse_mode_changed:
					self.is_reverse_mode_changed = False
					self.gas_direction, self.gas_time_delay = self.calculate_gas_time_delay(self.current_gas_value)
					
				if self.gas_direction == 'up':
					up = True
				else:
					down = True
				changed = True
				
		elif self.macro_mode == 1:
			H = self.light_dimensions[1]
			desired_height = round(self.current_gas_value * H)
			if self.chase_pixel[1] + 1 != desired_height:
				changed = True

		if changed:
			if self.macro_mode == 0:
				# shift the sequence
				packet = Lights.shift_packet(self.main_packet_plan.get_current_packet(), 1, left=left, right=right, up=up, down=down)
				self.main_packet_plan = PacketPlan([packet])
				self.update_lights()
				
			elif self.macro_mode == 1:
				reached_target, hit_walls = self.move_chase_pixel(self.main_packet_plan.get_current_packet(), left=left, right=right, up=up, down=down, height_val=desired_height)
				if reached_target:
					self.make_game_board(chase_position=self.chase_pixel)
					pulse_plan = PacketPlan(Lights.make_pulse_packet_plan(Lights.rgb_from_color('green'), self.light_dimensions, frames=6), time_delay=0.05)
					self.temp_packet_plans.append(pulse_plan)
					
				self.main_packet_plan = PacketPlan([self.draw_game_board()])
				self.main_packet_plan.last_motion_step_time = current_time
				self.update_lights()
	
	def move_chase_pixel(self, packet, left=None, right=None, up=None, down=None, height_val=None):
		L, H, D = self.light_dimensions
		x, y, z = self.chase_pixel
		reached_target = False
		hit_wall = False
		
		if left:
			x = x if x == 0 else x - 1
		if right:
			x = x if x == L - 1 else x + 1
			
		lr_pixel = x, y, z
		if lr_pixel in self.walls:
			hit_wall = True
			return reached_target, hit_wall
		
		if lr_pixel == self.target_pixel:
			reached_target = True
			self.chase_pixel = lr_pixel
			return reached_target, hit_wall
		
		# if up:
			# y = y if y == 0 else y - 1
		# if down:
			# y = y if y == H - 1 else y + 1
		
		ud_pixel = lr_pixel
		if height_val is not None:
			delta = height_val - y
			if delta < 0:
				step_val = -1
			else:
				step_val = 1
			
			for step in range(0, abs(delta)):
				new_y = y + step_val
				if new_y < 0:
					new_y = 0
				elif new_y > H - 1:
					new_y = H - 1
					
				new_ud_pixel = x, new_y, z
				if new_ud_pixel in self.walls:
					hit_wall = True
					self.chase_pixel = ud_pixel
					return reached_target, hit_wall
				
				if new_ud_pixel == self.target_pixel:
					reached_target = True
					self.chase_pixel = ud_pixel
				
				ud_pixel = new_ud_pixel
		
		# ud_pixel = x, y, z
		# if ud_pixel in self.walls:
			# hit_wall = True
			# self.chase_pixel = lr_pixel
			# return reached_target, hit_wall
		
		# if ud_pixel == self.target_pixel:
			# reached_target = True
			# self.chase_pixel = lr_pixel
			# return reached_target, hit_wall
			
		# TODO: add 3rd dimension
		
		self.chase_pixel = ud_pixel
		return reached_target, hit_wall
		
	def make_game_board(self, chase_position=(0,0,0)):
		L, H, D = self.light_dimensions
		num_pixels = L * H * D
		num_wall_pixels = int(num_pixels / 5)
		
		# create walls
		self.walls = []
		for i in range(num_wall_pixels):
			wall = chase_position
			while wall == chase_position or wall in self.walls:
				wall = (random.randrange(0, L), random.randrange(0, H), random.randrange(0, D))
			self.walls.append(wall)
		
		# create a target randomly on the board and make sure it isn't on the chase pixel or on the walls
		target = chase_position
		while target == chase_position or target in self.walls:
			target = (random.randrange(0, L), random.randrange(0, H), random.randrange(0, D))
			
		self.target_pixel = target
		
		print(f'Game board layout:')
		print(f'\tchase_pixel = {chase_position}')
		print(f'\ttarget_pixel = {self.target_pixel}')
		print(f'\twalls = {self.walls}')
		
	def draw_game_board(self):
		L, H, D = self.light_dimensions
		packet = Lights.make_whole_string_packet((255, 255, 255), self.light_dimensions, scale_value=0.1)
		for wall in self.walls:
			k, j, i = wall
			packet[i][j][k] = (255, 0, 0)
			
		k, j, i = self.target_pixel
		packet[i][j][k] = (0, 255, 0)
		
		k, j, i = self.chase_pixel
		packet[i][j][k] = (0, 0, 255)
		
		return packet
	
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
		
	def calculate_gas_time_delay(self, normalized_gas_value):
		# don't scroll at all when gas pedal is off
		# scroll fast when pressed all the way in
		x = normalized_gas_value
		if x == 0:
			return None, None	
		else:
			direction = 'down' if self.is_reverse_mode else 'up'
			a = .1
			delay = a*x*x - 1.2*a*x - 0.5625*x + 0.2*a + 0.6125
			
			return direction, delay
		
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
			
			
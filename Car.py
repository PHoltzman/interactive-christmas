import threading
import random
from datetime import datetime, timedelta

import global_vars
from BaseController import BaseController, PacketPlan
from Lights import Lights
from ChaseGame import ChaseGame
from SnakeGame import SnakeGame


class Car(BaseController):
	def __init__(self, controller, logger, name, light_dimensions, light_sender, gui):
		super().__init__(controller, logger, name, light_dimensions, light_sender, gui)
		
		self.macro_mode = 0
		self.select_mode = 0
		self.segment_size = 1
		self.current_colors = ['green', 'red']

		self.current_wheel_value = 0
		self.current_gas_value = 0
		self.current_brake_value = 0
		self.current_paddle_value = 0
		
		self.wheel_direction, self.wheel_time_delay = self.calculate_wheel_time_delay(self.current_wheel_value)
		self.gas_direction, self.gas_time_delay = self.calculate_gas_time_delay(self.current_gas_value)
		self.brake_direction, self.brake_time_delay = self.calculate_brake_time_delay(self.current_brake_value)
		self.paddle_direction, self.paddle_time_delay = self.calculate_paddle_time_delay(self.current_paddle_value)
		self.paddle_click_direction = None
		
		self.last_motion_step_time_wheel = self.last_input_datetime
		self.last_motion_step_time_gas = self.last_input_datetime
		self.last_motion_step_time_brake = self.last_input_datetime
		self.last_motion_step_time_paddle = self.last_input_datetime

		self.main_packet_plan = PacketPlan()
		self.temp_packet_plans = []
		
		self.chase_game = None
		self.snake_game = None
		
		self.logger.info(f'Car Macro Mode = {self.macro_mode}')
			
	def update_pixel_allocation(self, light_dimensions, **kwargs):
		self.light_dimensions = light_dimensions
		L, H, D = light_dimensions
		if L == 0 or H == 0 or D == 0:
			self.main_packet_plan = PacketPlan()
			self.temp_packet_plans = []
		else:
			starting_snake_length = len(self.snake_game.snake) if self.snake_game is not None else None
			self.main_packet_plan = self.make_packet_plan(starting_snake_length=starting_snake_length)
		
		self.update_lights()
			
	def check_for_inactivity(self):
		if self.is_active:
			if (datetime.now() - self.last_input_datetime).total_seconds() > 25:
				# this controller is now inactive so do stuff accordingly
				self.is_active = False
				self.macro_mode = 0
				self.select_mode = 0
				self.current_colors = ['green', 'red']
				self.current_paddle_value = 0
				self.paddle_direction, self.paddle_time_delay = self.calculate_paddle_time_delay(self.current_paddle_value)
				self.paddle_click_direction = None
				self.chase_game = None
				self.snake_game = None
								
				# tell the rest of the system that they can release our pixels
				self.light_sender.go_inactive(self.name)
		
		if not global_vars.STOP_THREADS:
			t = threading.Timer(5, self.check_for_inactivity).start()
	
	def on_button_pressed(self, button):
		super().on_button_pressed(button)
		color = self.get_friendly_button_name(button)
	
	def on_button_released(self, button):
		super().on_button_released(button)
		
		color = self.get_friendly_button_name(button)
		self.logger.info(f"{color} release")
		
		if color == 'up_left':	
			# for macro_mode 1, change the number of enemies
			if self.macro_mode == 1 and self.chase_game is not None:
				self.chase_game.update_enemies()
					
				self.main_packet_plan = self.make_packet_plan()
				self.update_lights()
				
			elif self.macro_mode == 2 and self.snake_game is not None:
				# for snake game, change the speed (but don't recreate board)
				self.snake_game.update_speed()
			
		elif color == 'up_right':
			# for macro_mode 0, change the colors and number of colors randomly
			if self.macro_mode == 0:
				num_colors = random.randint(2,3)
				color_list = random.sample(Lights.COLOR_LIST, num_colors)
				random.shuffle(color_list)
				self.current_colors = color_list
				
				self.main_packet_plan = self.make_packet_plan()
				self.update_lights()
			
			# for macro_mode 1, toggle through wall densities
			elif self.macro_mode == 1 and self.chase_game is not None:
				self.chase_game.update_wall_density()
				
				self.main_packet_plan = self.make_packet_plan()
				self.update_lights()
															
		elif color == 'down_left':
			if self.macro_mode == 0:
				# change the mode between alternating and blocks
				self.select_mode = 0 if self.select_mode == 1 else self.select_mode + 1
				self.logger.info(f'Car Select Mode = {self.select_mode}')
				
				self.main_packet_plan = self.make_packet_plan()
				self.update_lights()
				
			elif self.macro_mode == 1 and self.chase_game is not None:
				# change between 2d and 3d for chase game
				self.chase_game.toggle_3d()
				self.main_packet_plan = self.make_packet_plan()
				self.update_lights()
				
			elif self.macro_mode == 2 and self.snake_game is not None:
				# change between 2d and 3d for snake game
				self.snake_game.toggle_3d()
				self.main_packet_plan = self.make_packet_plan(starting_snake_length=len(self.snake_game.snake))
				self.update_lights()
				
		elif color == 'down_right':
			# toggle macro modes between light control and games
			# 0 = lights, 1 = chase game, 2 = snake game
			self.macro_mode = 0 if self.macro_mode == 2 else self.macro_mode + 1
			self.logger.info(f'Car Macro Mode = {self.macro_mode}')
			self.main_packet_plan = self.make_packet_plan(include_intro_screen=True)
			self.light_sender.write_log_entry(self.name, f"mode_{self.macro_mode}_active")
			self.update_lights()
			
		elif color in ['paddle_up', 'paddle_down']:
			# mode 0: change the speed for the z axis 
			# mode 1: move in the z axis one pixel
			# mode 2: set direction of motion to be forward or backward
			
			if color == 'paddle_up':
				if self.macro_mode == 0:
					if self.current_paddle_value < 5:
						self.current_paddle_value += 1
					self.paddle_direction, self.paddle_time_delay = self.calculate_paddle_time_delay(self.current_paddle_value)
				else:
					self.paddle_click_direction = 'forward'
					if self.snake_game is not None:
						self.snake_game.set_direction(self.paddle_click_direction)
						
			elif color == 'paddle_down':
				if self.macro_mode == 0:
					if self.current_paddle_value > -5:
						self.current_paddle_value -= 1
					self.paddle_direction, self.paddle_time_delay = self.calculate_paddle_time_delay(self.current_paddle_value)
				else:
					self.paddle_click_direction = 'backward'
					if self.snake_game is not None:
						self.snake_game.set_direction(self.paddle_click_direction)
			
	def make_packet_plan(self, starting_snake_length=None, include_intro_screen=False):
		L, H, D = self.light_dimensions
		packets = []
		
		if self.macro_mode == 0:
			colors_rgb = [Lights.rgb_from_color(x) for x in self.current_colors]
			if self.select_mode == 0:
				# blocks
				packet = Lights.get_blocks_packet(colors_rgb, self.light_dimensions)
				packets.append(packet)
					
			elif self.select_mode == 1:
				# alternating
				packet = Lights.get_alternating_packet(colors_rgb, self.light_dimensions, self.segment_size)
				packets.append(packet)
		
		elif self.macro_mode == 1:
			# chase game
			kwargs = {}
			if self.chase_game is not None:
				kwargs['is_3d'] = self.chase_game.is_3d
				kwargs['num_enemies'] = self.chase_game.num_enemies
				kwargs['wall_density_divisor_index'] = self.chase_game.wall_density_divisor_index
			self.chase_game = ChaseGame(self.logger, self.light_dimensions, self.light_sender, gui=self.gui, **kwargs)
			self.chase_game.make_new_game()
			packets.append(self.chase_game.draw_game_board())
			
		elif self.macro_mode == 2:
			# snake game
			if self.snake_game is not None:
				self.snake_game = SnakeGame.create_new(existing=self.snake_game, light_dimensions=self.light_dimensions)
			else:
				self.snake_game = SnakeGame(logger=self.logger, light_dimensions=self.light_dimensions, light_sender=self.light_sender, gui=self.gui)
			intro_packet_plans = self.snake_game.make_new_game(starting_snake_length=starting_snake_length, include_intro_screen=include_intro_screen)
			self.temp_packet_plans += intro_packet_plans
			packets.append(self.snake_game.draw_game_board())
			
		return PacketPlan(packets)

	def on_axis_moved(self, axis):
		super().on_axis_moved(axis)
		device, value, value2 = self.get_axis_details(axis)
		L, H, D = self.light_dimensions
		
		is_changed = False
		if device == 'gas_wheel':
			normalized_gas_value = round((value + 1) / 2 * -1 + 1, 2)  # normalizes gas value to range of 0 (off) to 1 (on) with 2 decimal precision
			if normalized_gas_value != self.current_gas_value:
				# this means the pedal position has changed so we need to process it
				is_changed = True
				self.current_gas_value = normalized_gas_value
				self.gas_direction, self.gas_time_delay = self.calculate_gas_time_delay(normalized_gas_value)
				if self.snake_game is not None:
					self.snake_game.set_direction(self.gas_direction)
			
			# process steering wheel horizontal motion
			if value2 is not None:
				normalized_wheel_value = round(value2, 1)
				if normalized_wheel_value != self.current_wheel_value:
					# this means the wheel has moved so we need to process it
					is_changed = True
					self.current_wheel_value = normalized_wheel_value
					self.wheel_direction, self.wheel_time_delay = self.calculate_wheel_time_delay(normalized_wheel_value)
					if self.snake_game is not None:
						self.snake_game.set_direction(self.wheel_direction)
			
		elif device == 'brake':
			normalized_brake_value = round(value, 1)  # normalizes brake value to range of 0 (off) to 1 (on) with 2 decimal precision
			if normalized_brake_value != self.current_brake_value:
				# this means the pedal position has changed so we need to process it
				is_changed = True
				self.current_brake_value = normalized_brake_value
				self.brake_direction, self.brake_time_delay = self.calculate_brake_time_delay(normalized_brake_value)
				if self.snake_game is not None:
					self.snake_game.set_direction(self.brake_direction)
		
		else:
			self.logger.info(f'{device} {value} {value2}')
			
		if is_changed:
			self.update_lights()
			
	def update_lights(self):
		# invoke light updater
		new_packet = self.main_packet_plan.get_current_packet()
		if self.temp_packet_plans:
			packets_to_merge = [new_packet] + [x.get_current_packet() for x in self.temp_packet_plans]
			try:
				new_packet = Lights.merge_packets(packets_to_merge, self.light_dimensions)
			except TypeError:
				for item in self.temp_packet_plans:
					print(len(item.packet_time_series))
				raise
			except IndexError:
				self.logger.warning('Index error when merging packets, likely due to light dimensions being reallocated. Skipping merge and using main packet instead and expecting it to fix itself next time around')
		
		self.light_sender.set_lights(self.name, new_packet)
		
	def next_moving_step(self, current_time):
		# determine when a sequence should be shifted
		right = False
		left = False
		up = False
		down = False
		forward = False
		backward = False
		changed = False
		enemy_changed = False
		
		# handle current temp packet plans
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
			# if direction is not None, that means some control is engaged so we want motion
			# if the current_time is greater than the last motion time by at least the time_delay amount, then we need to do a motion step
			if self.wheel_direction is not None and (current_time - self.last_motion_step_time_wheel).total_seconds() >= self.wheel_time_delay:
				self.last_motion_step_time_wheel = current_time
				if self.wheel_direction == 'right':
					right = True
				else:
					left = True
				changed = True
				
			# gas pedal behavior changes between macro modes as does paddle shifter behavior
			# in mode 0, it controls the speed of motion and the reverse button controls direction up or down
			# in mode 1, it controls height above the bottom, with gravity pulling the pixel back down when the gas pedal is released
			if self.macro_mode == 0:
				if self.gas_direction is not None and (current_time - self.last_motion_step_time_gas).total_seconds() >= self.gas_time_delay:
					self.last_motion_step_time_gas = current_time
					up = True
					changed = True
					
				if self.brake_direction is not None and (current_time - self.last_motion_step_time_brake).total_seconds() >= self.brake_time_delay:
					self.last_motion_step_time_brake = current_time
					down = True
					changed = True
					
				if self.paddle_direction is not None and (current_time - self.last_motion_step_time_paddle).total_seconds() >= self.paddle_time_delay:
					self.last_motion_step_time_paddle = current_time
					if self.paddle_direction == 'forward':
						forward = True
					else:
						backward = True
					changed = True
			
				if changed:
					# shift the sequence
					packet = Lights.shift_packet(self.main_packet_plan.get_current_packet(), 1, left=left, right=right, up=up, down=down, forward=forward, backward=backward)
					self.main_packet_plan = PacketPlan([packet])
					self.main_packet_plan.last_motion_step_time = current_time
					self.update_lights()
		
		elif self.macro_mode == 1 and self.chase_game is not None:
			if self.wheel_direction is not None and (current_time - self.last_motion_step_time_wheel).total_seconds() >= self.wheel_time_delay:
				self.last_motion_step_time_wheel = current_time
				if self.wheel_direction == 'right':
					right = True
				else:
					left = True
					
			H = self.light_dimensions[1]
			desired_height = round(self.current_gas_value * H)
			
			if self.paddle_click_direction is not None:
				if self.paddle_click_direction == 'forward':
					forward = True
				else:
					backward = True
				self.paddle_click_direction = None
			
			# for chase game, we always need to call out because there might be enemy movement even if no controller input
			packet, pulse_plans = self.chase_game.next_moving_step(
				current_time, 
				left=left, 
				right=right,
				forward=forward,
				backward=backward,
				desired_height=desired_height
			)
			self.temp_packet_plans += pulse_plans
			
			if packet is not None:
				self.main_packet_plan = PacketPlan([packet])
				self.main_packet_plan.last_motion_step_time = current_time
				self.update_lights()
				
		elif self.macro_mode == 2 and self.snake_game is not None:
			# for snake game, just call out to the game and let it decide what to do since all direction input is asynchronously set
			packet, pulse_plans = self.snake_game.next_moving_step(current_time)
			self.temp_packet_plans += pulse_plans
			
			if packet is not None:
				# if a None packet is returned, then just keep reusing the existing packet
				self.main_packet_plan = PacketPlan([packet])
				self.main_packet_plan.last_motion_step_time = current_time
				changed = True
			
			if changed:
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
			"button_trigger_r": "down_right",
			"button_a": "paddle_down",
			"button_b": "paddle_up"
		}
		try:
			return button_mapping[button.name]
		except KeyError:
			return button.name
		
	@staticmethod
	def calculate_gas_time_delay(value):
		# don't scroll at all when gas pedal is off
		# scroll fast when pressed all the way in
		x = value
		if x == 0:
			return None, None	
		else:
			direction = 'up'
			a = .1
			delay = a*x*x - 1.2*a*x - 0.5625*x + 0.2*a + 0.6125
			
			return direction, delay
			
	@staticmethod
	def calculate_brake_time_delay(value):
		# don't scroll at all when brake pedal is off
		# scroll fast when pressed all the way in
		x = value
		if x == 0:
			return None, None	
		else:
			direction = 'down'
			a = .1
			delay = a*x*x - 1.2*a*x - 0.5625*x + 0.2*a + 0.6125
			
			return direction, delay
	
	@staticmethod
	def calculate_paddle_time_delay(paddle_value):
		if paddle_value == 0:
			return None, None
		else:
			if paddle_value > 0:
				direction = 'forward'
			else:
				direction = 'backward'
				
			val = abs(paddle_value)
			
			if val == 1:
				delay = 0.5
			elif val == 2:
				delay = 0.3
			elif val == 3:
				delay = 0.2
			elif val == 4:
				delay = 0.1
			else:
				delay = 0.05
			
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
			
			
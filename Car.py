import threading
import random
from datetime import datetime, timedelta

from BaseController import BaseController, PacketPlan
from Lights import Lights


class Car(BaseController):
	def __init__(self, controller, logger, name, light_dimensions, light_sender, gui):
		super().__init__(controller, logger, name, light_dimensions, light_sender, gui)
		
		self.macro_mode = 0
		self.select_mode = 0
		self.segment_size = 1
		self.dim_ratio = 0
		self.current_wheel_value = 0
		self.current_gas_value = 0
		self.current_brake_value = 0
		self.current_paddle_value = 0
		
		self.wheel_direction, self.wheel_time_delay = self.calculate_wheel_time_delay(self.current_wheel_value)
		self.gas_direction, self.gas_time_delay = self.calculate_gas_time_delay(self.current_gas_value)
		self.brake_direction, self.brake_time_delay = self.calculate_brake_time_delay(self.current_brake_value)
		self.paddle_direction, self.paddle_time_delay = self.calculate_paddle_time_delay(self.current_paddle_value)
		self.paddle_click_direction = None
		self.enemy_time_delay = 0.5
		
		self.last_motion_step_time_wheel = self.last_input_datetime
		self.last_motion_step_time_gas = self.last_input_datetime
		self.last_motion_step_time_brake = self.last_input_datetime
		self.last_motion_step_time_paddle = self.last_input_datetime
		self.last_motion_step_time_enemy = self.last_input_datetime

		self.current_colors = ['green', 'black']
		self.main_packet_plan = PacketPlan()
		self.temp_packet_plans = []
		
		# used for macro_mode 1
		self.wall_density_divisor_list = [10000, 20, 10, 8, 6, 5]
		self.target_pixel = None
		self.chase_pixel = None
		self.wall_density_divisor = self.wall_density_divisor_list[0]
		self.num_enemies = 0
		self.enemies = []
		self.walls = []
		
		self.logger.info(f'Car Macro Mode = {self.macro_mode}')
			
	def update_pixel_allocation(self, light_dimensions):
		self.light_dimensions = light_dimensions
		L, H, D = light_dimensions
		if L == 0 or H == 0 or D == 0:
			self.main_packet_plan = PacketPlan()
			self.temp_packet_plans = []
		else:
			self.main_packet_plan = self.make_packet_plan()
		
		
		self.update_lights()
			
	def check_for_inactivity(self):
		if self.is_active:
			if (datetime.now() - self.last_input_datetime).total_seconds() > 15:
				# this controller is now inactive so do stuff accordingly
				self.is_active = False
				self.macro_mode = 0
				self.num_enemies = 0
				self.wall_density_divisor = self.wall_density_divisor_list[0]
				self.current_colors = ['green', 'black']
				self.current_paddle_value = 0
				self.paddle_direction, self.paddle_time_delay = self.calculate_paddle_time_delay(self.current_paddle_value)
				self.paddle_click_direction = None
								
				# tell the rest of the system that they can release our pixels
				self.light_sender.go_inactive(self.name)
			
		t = threading.Timer(5, self.check_for_inactivity).start()
	
	def on_button_pressed(self, button):
		super().on_button_pressed(button)
		color = self.get_friendly_button_name(button)
	
	def on_button_released(self, button):
		super().on_button_released(button)
		
		color = self.get_friendly_button_name(button)
		self.logger.info(f"{color} release")
		
		packet_plan = []
		if color == 'up_left':	
			# for macro_mode 1, change the number of enemies
			if self.macro_mode == 1:
				if self.num_enemies < 3:
					self.num_enemies += 1
				else:
					self.num_enemies = 0
					
				self.main_packet_plan = self.make_packet_plan()
				self.update_lights()
			
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
			elif self.macro_mode == 1:
				ind = self.wall_density_divisor_list.index(self.wall_density_divisor)
				ind += 1
				if ind > len(self.wall_density_divisor_list) - 1:
					ind = 0
					
				self.wall_density_divisor = self.wall_density_divisor_list[ind]
				
				self.main_packet_plan = self.make_packet_plan()
				self.update_lights()
											
		elif color == 'down_left':
			# change the mode between alternating and blocks
			self.select_mode = 0 if self.select_mode == 1 else self.select_mode + 1
			self.logger.info(f'Car Select Mode = {self.select_mode}')
			
			self.main_packet_plan = self.make_packet_plan()
			self.update_lights()
			
		elif color == 'down_right':
			# toggle macro modes between light control and the "chase the pixel" game
			# 0 = lights, 1 = game
			self.macro_mode = 0 if self.macro_mode == 1 else self.macro_mode + 1
			self.logger.info(f'Car Macro Mode = {self.macro_mode}')			
			self.main_packet_plan = self.make_packet_plan()
			self.light_sender.write_log_entry(self.name, f"mode_{self.macro_mode}_active")
			self.update_lights()
			
		elif color in ['paddle_up', 'paddle_down']:
			# mode 0: change the speed for the z axis 
			# mode 1: move in the z axis one pixel
			
			if color == 'paddle_up':
				if self.macro_mode == 0:
					if self.current_paddle_value < 5:
						self.current_paddle_value += 1
					self.paddle_direction, self.paddle_time_delay = self.calculate_paddle_time_delay(self.current_paddle_value)
				else:
					self.paddle_click_direction = 'forward'
			
			elif color == 'paddle_down':
				if self.macro_mode == 0:
					if self.current_paddle_value > -5:
						self.current_paddle_value -= 1
					self.paddle_direction, self.paddle_time_delay = self.calculate_paddle_time_delay(self.current_paddle_value)
				else:
					self.paddle_click_direction = 'backward'
			
	def make_packet_plan(self):
		L, H, D = self.light_dimensions
		packets = []
		
		if self.macro_mode == 0:
			colors_rgb = [Lights.rgb_from_color(x) for x in self.current_colors]
			if self.select_mode == 0:
				# blocks
				packet = Lights.get_blocks_packet(colors_rgb, self.light_dimensions)
				for i in range(L):
					packets.append(Lights.shift_packet(packet, i, right=True))
					
			elif self.select_mode == 1:
				# alternating
				packet = Lights.get_alternating_packet(colors_rgb, self.light_dimensions, self.segment_size)
				for i in range(len(colors_rgb)):
					for j in range(self.segment_size):
						packets.append(Lights.shift_packet(packet, i * self.segment_size + j + 1, right=True))
		
		elif self.macro_mode == 1:
			self.chase_pixel = (0,0,0)
			self.make_game_board(chase_position=self.chase_pixel)
			packets.append(self.draw_game_board())
		
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
			
			# process steering wheel horizontal motion
			if value2 is not None:
				normalized_wheel_value = round(value2, 1)
				if normalized_wheel_value != self.current_wheel_value:
					# this means the wheel has moved so we need to process it
					is_changed = True
					self.current_wheel_value = normalized_wheel_value
					self.wheel_direction, self.wheel_time_delay = self.calculate_wheel_time_delay(normalized_wheel_value)
			
		elif device == 'brake':
			normalized_brake_value = round(value, 2)  # normalizes brake value to range of 0 (off) to 1 (on) with 2 decimal precision
			if normalized_brake_value != self.current_brake_value:
				# this means the pedal position has changed so we need to process it
				is_changed = True
				self.current_brake_value = normalized_brake_value
				self.brake_direction, self.brake_time_delay = self.calculate_brake_time_delay(normalized_brake_value)
		
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
		
		# if direction is not None, that means the wheel/gas is engaged so we want motion
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
				
		elif self.macro_mode == 1:
			H = self.light_dimensions[1]
			desired_height = round(self.current_gas_value * H)
			if self.chase_pixel[1] + 1 != desired_height:
				changed = True
				
			if self.paddle_click_direction is not None:
				if self.paddle_click_direction == 'forward':
					forward = True
				else:
					backward = True
				self.paddle_click_direction = None
				changed = True
				
		if self.macro_mode == 1 and (current_time - self.last_motion_step_time_enemy).total_seconds() >= self.enemy_time_delay:
			self.last_motion_step_time_enemy = current_time
			changed = True
			enemy_changed = True
		
		if changed:
			if self.macro_mode == 0:
				# shift the sequence
				packet = Lights.shift_packet(self.main_packet_plan.get_current_packet(), 1, left=left, right=right, up=up, down=down, forward=forward, backward=backward)
				self.main_packet_plan = PacketPlan([packet])
				self.update_lights()
				
			elif self.macro_mode == 1:
				reached_target, hit_walls, hit_enemy = self.move_chase_pixel(self.main_packet_plan.get_current_packet(), 
																	left=left, right=right, up=up, down=down, 
																	forward=forward, backward=backward,
																	height_val=desired_height)
				
				if hit_enemy:
					# make a brand new game board
					self.logger.info('Hit enemy at location: {self.chase_pixel}')
					self.chase_pixel = (0,0,0)
					self.make_game_board(chase_position=self.chase_pixel)
					pulse_plan = PacketPlan(Lights.make_pulse_packet_plan(Lights.rgb_from_color('red'), self.light_dimensions, frames=6), time_delay=0.05)
					self.temp_packet_plans.append(pulse_plan)
				
				elif reached_target:
					# make a new game board but keep the chase pixel and the enemies in current locations
					self.logger.info(f'Reached target at location: {self.chase_pixel}')
					self.make_game_board(chase_position=self.chase_pixel, create_new_enemies=False)
					pulse_plan = PacketPlan(Lights.make_pulse_packet_plan(Lights.rgb_from_color('green'), self.light_dimensions, frames=6), time_delay=0.05)
					self.temp_packet_plans.append(pulse_plan)
				
				elif enemy_changed:
					any_hit_target = False
					new_enemies = []
					for enemy in self.enemies:
						if not any_hit_target:
							# if an earlier one hit the target, then don't check the next ones, just keep them where they are
							new_enemy, enemy_reached_target, enemy_hit_walls = self.move_enemy_pixel(self.main_packet_plan.get_current_packet(), enemy) 
							if enemy_reached_target:
								# this means the enemy moved onto the chase pixel and we should flash red and make a new game board
								any_hit_target = True
								self.chase_pixel = (0,0,0)
								self.make_game_board(chase_position=self.chase_pixel)
								pulse_plan = PacketPlan(Lights.make_pulse_packet_plan(Lights.rgb_from_color('red'), self.light_dimensions, frames=6), time_delay=0.05)
								self.temp_packet_plans.append(pulse_plan)
							
						else:
							# just keep the enemy where it is as the starting point for next time since a different one hit the target
							new_enemy = enemy
							
						# add the enemy back to the list
						new_enemies.append(new_enemy)
							
					self.enemies = new_enemies
										
				self.main_packet_plan = PacketPlan([self.draw_game_board()])
				self.main_packet_plan.last_motion_step_time = current_time
				self.update_lights()
	
	def move_enemy_pixel(self, packet, enemy_pixel):
		# pick a direction to move based on where the chase pixel is and try it
		# if the new location is not different than the current location, then try a different direction
		# we are only moving one cardinal direction at a time so this should be simple
		a, b, c = self.chase_pixel
		x, y, z = enemy_pixel
		
		delta_x = a - x			
		delta_y = b - y
		delta_z = c - z
		movement_list = [
			("right", -delta_x),
			("left", delta_x),
			("up", -delta_y),
			("down", delta_y),
			("forward", -delta_z),
			("backward", delta_z)
		]
		movement_list.sort(key=lambda x: x[1])
		
		for step in movement_list:
			new_location, reached_target, hit_wall, hit_enemy = self.move_pixel(enemy_pixel, self.chase_pixel, [], packet, **{step[0]:True})
			if new_location != enemy_pixel:
				# this means we actually moved successfully so can stop trying additional directions
				return new_location, reached_target, hit_wall
				
		# if we couldn't move at all (unlikely), then return this
		return enemy_pixel, False, True
	
	def move_chase_pixel(self, packet, left=None, right=None, up=None, down=None, forward=None, backward=None, height_val=None):
		new_location, reached_target, hit_wall, hit_enemy = self.move_pixel(self.chase_pixel, self.target_pixel, self.enemies, packet, 
																			left, right, up, down, forward, backward, height_val)
		self.chase_pixel = new_location
		return reached_target, hit_wall, hit_enemy
	
	def move_pixel(self, pixel, target_pixel, enemy_pixels, packet, left=None, right=None, up=None, down=None, forward=None, backward=None, height_val=None):
		L, H, D = self.light_dimensions
		# self.logger.info(f"{L} {H} {D}")
		x, y, z = pixel
		reached_target = False
		hit_wall = False
		hit_enemy = False
		
		# first move the pixel left and right and check for collisions or reaching the target
		if left:
			x = x if x == 0 else x - 1
		if right:
			x = x if x == L - 1 else x + 1
			
		lr_pixel = x, y, z
		if lr_pixel in self.walls:
			hit_wall = True
			return pixel, reached_target, hit_wall, hit_enemy
			
		if lr_pixel in enemy_pixels:
			hit_enemy = True
			return pixel, reached_target, hit_wall, hit_enemy
		
		if lr_pixel == target_pixel:
			reached_target = True
			return lr_pixel, reached_target, hit_wall, hit_enemy
			
		# then move the pixel forward and backward and check for collisions or reaching the target
		if backward:
			z = z if z == 0 else z - 1
		if forward:
			z = z if z == D - 1 else z + 1
			
		fb_pixel = x, y, z
		if fb_pixel in self.walls:
			hit_wall = True
			return lr_pixel, reached_target, hit_wall, hit_enemy
			 
		if fb_pixel in enemy_pixels:
			hit_enemy = True
			return lr_pixel, reached_target, hit_wall, hit_enemy
		
		if fb_pixel == target_pixel:
			reached_target = True
			return fb_pixel, reached_target, hit_wall, hit_enemy
		
		# finally, move the pixel up or down, which is more challenging due to the gravity behavior with the gas pedal
		ud_pixel = fb_pixel
		if height_val is not None:
			# normal case for chase pixel
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
					return ud_pixel, reached_target, hit_wall, hit_enemy
					
				if new_ud_pixel in enemy_pixels:
					hit_enemy = True
					return new_ud_pixel, reached_target, hit_wall, hit_enemy
				
				if new_ud_pixel == self.target_pixel:
					reached_target = True
					return new_ud_pixel, reached_target, hit_wall, hit_enemy
				
				ud_pixel = new_ud_pixel
		else:
			# case for moving enemy pixels
			if down:
				y = y if y == 0 else y - 1
			if up:
				y = y if y == H - 1 else y + 1
			
			ud_pixel = x, y, z
			if ud_pixel in self.walls:
				hit_wall = True
				return fb_pixel, reached_target, hit_wall, hit_enemy
				
			if ud_pixel in enemy_pixels:
				hit_enemy = True
				return ud_pixel, reached_target, hit_wall, hit_enemy
			
			if ud_pixel == self.target_pixel:
				reached_target = True
				return ud_pixel, reached_target, hit_wall, hit_enemy
		
		return ud_pixel, reached_target, hit_wall, hit_enemy
		
	def make_game_board(self, chase_position=(0,0,0), create_new_enemies=True):
		L, H, D = self.light_dimensions
		num_pixels = L * H * D
		num_wall_pixels = int(num_pixels / self.wall_density_divisor)
		
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
		
		# create enemies on the board (if they are not already there)
		if create_new_enemies:
			enemy_list = []
			for i in range(self.num_enemies):
				x = True
				while(x):
					enemy = (random.randrange(0, L), random.randrange(0, H), random.randrange(0, D))
					if enemy not in enemy_list and enemy not in self.walls and enemy != chase_position:
						enemy_list.append(enemy)
						x = False
			self.enemies = enemy_list
		
		self.logger.info(
			f'''Game board layout:
				\tchase_pixel = {chase_position}
				\ttarget_pixel = {self.target_pixel}
				\twalls = {self.walls}
				\tenemies = {self.enemies}
			'''
		)
		
	def draw_game_board(self):
		L, H, D = self.light_dimensions
		packet = Lights.make_whole_string_packet((255, 255, 255), self.light_dimensions, scale_value=0.1)
		for wall in self.walls:
			k, j, i = wall
			packet[i][j][k] = (255, 255, 0)
			
		k, j, i = self.target_pixel
		packet[i][j][k] = (0, 255, 0)
		
		k, j, i = self.chase_pixel
		packet[i][j][k] = (0, 0, 255)
		
		for enemy in self.enemies:
			k, j, i = enemy
			packet[i][j][k] = (255, 0, 0)
		
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
			
			
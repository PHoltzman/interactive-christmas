import random
from datetime import datetime

from BaseController import PacketPlan
from Lights import Lights


class ChaseGame():

	MAX_ENEMIES = 3

	def __init__(self, logger, light_dimensions, light_sender, gui=None, wall_density_divisor_index=0, num_enemies=0, is_3d=False):
		self.logger = logger
		self.light_dimensions = light_dimensions
		self.light_sender = light_sender
		self.gui = gui
				
		self.enemy_time_delay = 0.5
		
		self.wall_density_divisor_index =  wall_density_divisor_index
		self.wall_density_divisor_list = [10000, 20, 10, 8, 6, 5]
		self.wall_density_divisor = self.wall_density_divisor_list[self.wall_density_divisor_index]
		
		self.num_enemies = num_enemies
		self.is_3d = is_3d
		
		L, H, D = self.light_dimensions
		self.target_pixel = (L-1, H-1, D-1)
		self.chase_pixel = (0, 0, 0)
		
		self.enemies = []
		self.walls = []
		
		self.last_motion_step_time = datetime.now()
		self.last_motion_step_time_enemy = datetime.now()
		
	def toggle_3d(self):
		self.is_3d = not self.is_3d
		
	def update_enemies(self, update_to_right=True):
		if update_to_right:
			if self.num_enemies < ChaseGame.MAX_ENEMIES:
				self.num_enemies += 1
			else:
				self.num_enemies = 0
		else:
			if self.num_enemies == 0:
				self.num_enemies -= 1
			else:
				self.num_enemies = ChaseGame.MAX_ENEMIES

	def update_wall_density(self, update_to_right=True):
		if update_to_right:
			if self.wall_density_divisor_index < len(self.wall_density_divisor_list) - 1:
				self.wall_density_divisor_index += 1
			else:
				self.wall_density_divisor_index = 0
		else:
			if self.wall_density_divisor_index > 0:
				self.wall_density_divisor_index -= 1
			else:
				self.wall_density_divisor_index = len(self.wall_density_divisor_list) - 1
			
		self.wall_density_divisor = self.wall_density_divisor_list[self.wall_density_divisor_index]
		
	def next_moving_step(self, current_time, left=None, right=None, forward=None, backward=None, desired_height=None):
		pulse_plan = None
		if not self.is_3d:
			forward=False
			backward=False
			
		if left or right or forward or backward or self.chase_pixel[1] + 1 != desired_height:
			reached_target, hit_walls, hit_enemy = self.move_chase_pixel( 
				left=left, right=right, forward=forward, backward=backward,
				height_val=desired_height
			)
						
			if hit_enemy:
				# make a brand new game board
				self.logger.info(f'Hit enemy at location: {self.chase_pixel}')
				self.chase_pixel = (0,0,0)
				self.make_new_game(chase_position=self.chase_pixel)
				packet = self.draw_game_board()
				pulse_plan = PacketPlan(Lights.make_pulse_packet_plan(Lights.rgb_from_color('red'), self.light_dimensions, frames=6), time_delay=0.05)
				return packet, pulse_plan
			
			if reached_target:
				# make a new game board but keep the chase pixel and the enemies in current locations
				self.logger.info(f'Reached target at location: {self.chase_pixel}')
				self.make_new_game(chase_position=self.chase_pixel, create_new_enemies=False)
				packet = self.draw_game_board()
				pulse_plan = PacketPlan(Lights.make_pulse_packet_plan(Lights.rgb_from_color('green'), self.light_dimensions, frames=6), time_delay=0.05)
				return packet, pulse_plan
		
		if (current_time - self.last_motion_step_time_enemy).total_seconds() >= self.enemy_time_delay:
			self.last_motion_step_time_enemy = current_time
			any_hit_target = False
			new_enemies = []
			for enemy in self.enemies:
				if not any_hit_target:
					# if an earlier one hit the target, then don't check the next ones, just keep them where they are
					new_enemy, enemy_reached_target, enemy_hit_walls = self.move_enemy_pixel(enemy) 
					if enemy_reached_target:
						# this means the enemy moved onto the chase pixel and we should flash red and make a new game board
						any_hit_target = True
						self.chase_pixel = (0,0,0)
						self.make_new_game(chase_position=self.chase_pixel)
						packet = self.draw_game_board()
						pulse_plan = PacketPlan(Lights.make_pulse_packet_plan(Lights.rgb_from_color('red'), self.light_dimensions, frames=6), time_delay=0.05)
						return packet, pulse_plan
					
				else:
					# just keep the enemy where it is as the starting point for next time since a different one hit the target
					new_enemy = enemy
					
				# add the enemy back to the list
				new_enemies.append(new_enemy)
					
			self.enemies = new_enemies
			
		packet = self.draw_game_board()
		return packet, pulse_plan
		
	def make_new_game(self, chase_position=(0,0,0), create_new_enemies=True):
		L, H, D = self.light_dimensions
		if not self.is_3d:
			D = 1
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
		packet = Lights.make_whole_string_packet(Lights.rgb_from_color('white'), self.light_dimensions, scale_value=0.1)
		for wall in self.walls:
			k, j, i = wall
			packet[i][j][k] = Lights.rgb_from_color('yellow')
			
		k, j, i = self.target_pixel
		packet[i][j][k] = Lights.rgb_from_color('green')
		
		k, j, i = self.chase_pixel
		packet[i][j][k] = Lights.rgb_from_color('blue')
		
		for enemy in self.enemies:
			k, j, i = enemy
			packet[i][j][k] = Lights.rgb_from_color('red')
		
		return packet
		
	def move_enemy_pixel(self, enemy_pixel):
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
			new_location, reached_target, hit_wall, hit_enemy = self.move_pixel(enemy_pixel, self.chase_pixel, [], **{step[0]:True})
			if new_location != enemy_pixel:
				# this means we actually moved successfully so can stop trying additional directions
				return new_location, reached_target, hit_wall
				
		# if we couldn't move at all (unlikely), then return this
		return enemy_pixel, False, True
	
	def move_chase_pixel(self, left=None, right=None, up=None, down=None, forward=None, backward=None, height_val=None):
		new_location, reached_target, hit_wall, hit_enemy = self.move_pixel(self.chase_pixel, self.target_pixel, self.enemies, 
																			left, right, up, down, forward, backward, height_val)
		self.chase_pixel = new_location
		return reached_target, hit_wall, hit_enemy
	
	def move_pixel(self, pixel, target_pixel, enemy_pixels, left=None, right=None, up=None, down=None, forward=None, backward=None, height_val=None):
		L, H, D = self.light_dimensions
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
		
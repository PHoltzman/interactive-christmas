import random
from datetime import datetime

from BaseController import PacketPlan
from Lights import Lights

class MazeGame():
	"""
	Navigate your pixel through a maze, avoiding hitting any walls. You can make it harder by increasing the speed and by changing to harder difficulties (including moving from 2D into 3D). In general, the same maze stays until it is completed or until a button is pressed to cycle to a new random one at the same difficulty.
	A 3 second countdown precedes the start of the maze to give people a chance to get ready.
	Speed is handled like in SnakeGame. The controller is only for setting direction of movement, not for controlling the speed of that movement.

	"""
	def __init__(self, logger, light_dimensions, light_sender, gui=None, speed_time_delay_index=0, wall_density_divisor_index=0, is_3d=False):
		self.logger = logger
		self.light_dimensions = light_dimensions
		self.light_sender = light_sender
		self.gui = gui
				
		self.speed_time_delay_index = speed_time_delay_index
		self.speed_time_delay_list = [1, 0.8, 0.6, 0.4, 0.3, 0.2]  # time delay in seconds between movements
		self.speed_time_delay = self.speed_time_delay_list[self.speed_time_delay_index]
		
		self.is_3d = is_3d
		
		self.last_motion_step_time = datetime.now()
		self.direction = self.get_new_motion_direction()
		
		self.current = 0, 0, 0
		self.path = []  # ordered array of pixels that define the maze from start to finish
		self.walls = []  # array of pixels representing walls. Hitting these is just like hitting the boundary of the board.
		
	def toggle_3d(self):
		self.is_3d = not self.is_3d
	
	def get_direction_list(self):
		x = ['right', 'left', 'up', 'down']
		if self.is_3d:
			x += ['forward', 'backward']
			
		return x
		
	def get_opposite_direction(self, direction):
		if direction == 'right':
			return 'left'
		elif direction == 'left':
			return 'right'
		elif direction == 'up':
			return 'down'
		elif direction == 'down':
			return 'up'
		elif direction == 'forward':
			return 'backward'
		elif direction == 'backward':
			return 'forward'
		else:
			return None
		
	def set_direction(self, direction):
		# update the current direction if it is valid for the 3Dness and if it isn't a 180 degree turn from current
		if direction in self.get_direction_list():
			if direction != self.get_opposite_direction(self.direction):
				self.direction = direction
			
	def update_speed(self, update_to_right=True):
		if update_to_right:
			if self.speed_time_delay_index < len(self.speed_time_delay_list) - 1:
				self.speed_time_delay_index += 1
			else:
				self.speed_time_delay_index = 0
		else:
			if self.speed_time_delay_index > 0:
				self.speed_time_delay_index -= 1
			else:
				self.speed_time_delay_index = len(self.speed_time_delay_list) - 1
			
		self.speed_time_delay = self.speed_time_delay_list[self.speed_time_delay_index]
		self.logger.info(f'Snake Game time delay set to {self.speed_time_delay} seconds')
		
	def next_moving_step(self, current_time):
		pulse_plan = None
		if (current_time - self.last_motion_step_time).total_seconds() >= self.speed_time_delay:
			hit_boundary, hit_self, hit_target = self.move_one_step()
			self.last_motion_step_time = current_time

			# if hit boundary, pulse red and start the game over by making a new board
			if hit_boundary:
				pulse_plan = PacketPlan(Lights.make_pulse_packet_plan(Lights.rgb_from_color('red'), self.light_dimensions, frames=6), time_delay=0.05)
				self.make_new_game()
				
			# if hit snake, pulse orange and start the game over by making a new board
			elif hit_self:
				pulse_plan = PacketPlan(Lights.make_pulse_packet_plan(Lights.rgb_from_color('orange'), self.light_dimensions, frames=6), time_delay=0.05)
				self.make_new_game()
			
			# if caught the next bite, quick pulse green and make a new target
			elif hit_target:
				pulse_plan = PacketPlan(Lights.make_pulse_packet_plan(Lights.rgb_from_color('green'), self.light_dimensions, frames=3), time_delay=0.05)
				self.target = self.make_target()
			
		# draw the board
		packet = self.draw_game_board()
		
		return packet, pulse_plan
		
	def move_one_step(self):
		L, H, D = self.light_dimensions
		x, y, z = self.snake[0]
		
		hit_boundary = False
		hit_self = False
		hit_target = False
				
		# first move the snake and verify it doesn't hit a wall
		if self.direction == 'right':
			x += 1
		elif self.direction == 'left':
			x -= 1
		elif self.direction == 'up':
			y += 1
		elif self.direction == 'down':
			y -= 1
		elif self.direction == 'forward':
			z += 1
		elif self.direction == 'backward':
			z -= 1
			
		if x < 0 or x >= L or y < 0 or y >= H or z < 0 or z >= D:
			hit_boundary = True
			return hit_boundary, hit_self, hit_target
					
		# if it reaches the target, the snake doesn't move for that step and the new pixel is just added to the front
		new = x, y, z
		self.snake.insert(0, new)
		
		if new == self.target:
			# if we hit the target, then we need to make a new one and we don't want to move the back of the snake this time around
			hit_target = True
		
		else:
			# we need to move the snake one step. We already added the new step so just need to remove off the back
			self.snake = self.snake[:-1]
		
		# once moved, verify we didn't run into our own body
		if self.snake.count(new) > 1:
			hit_self = True
			
		return hit_boundary, hit_self, hit_target
		
	def make_target(self):
		L, H, D = self.light_dimensions
		if not self.is_3d:
			D = 1
			
		target = self.snake[0]
		while target in self.snake:
			target = (random.randrange(0, L), random.randrange(0, H), random.randrange(0, D))
			
		return target
		
	def get_new_motion_direction(self):
		return random.choice(self.get_direction_list())
		
	def make_new_game(self):
		L, H, D = self.light_dimensions
		if not self.is_3d:
			D = 1
		num_pixels = L * H * D
		
		# pick an initial spot for the game to start (try not to be too close to a boundary)
		self.current = 0, 0, 0
		
		# pick a spot for the target
		self.target = self.make_target()
		
		# pick an initial direction of motion
		# self.direction = self.get_new_motion_direction()
		self.direction = 'right'
		
	def draw_game_board(self):
		L, H, D = self.light_dimensions
		packet = Lights.make_whole_string_packet(Lights.rgb_from_color('white'), self.light_dimensions, scale_value=0.05)
		snake_colors = Lights.make_gradient_colors(
			len(self.snake), 
			Lights.rgb_from_color('green'), 
			Lights.rgb_from_color('yellow')
		)
		for s, item in enumerate(self.snake):
			k, j, i = item
			packet[i][j][k] = snake_colors[s]
		
		k, j, i = self.target
		packet[i][j][k] = Lights.rgb_from_color('teal')
		
		return packet
		
	
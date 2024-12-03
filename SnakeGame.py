import random
from datetime import datetime, timedelta

from BaseController import PacketPlan
from Lights import Lights

class SnakeGame():

	def __init__(self, logger, light_dimensions, light_sender, gui=None, speed_time_delay_index=1, is_3d=False):
		self.logger = logger
		self.light_dimensions = light_dimensions
		self.light_sender = light_sender
		self.gui = gui
				
		self.speed_time_delay_index = speed_time_delay_index
		self.speed_time_delay_list = [0.8, 0.6, 0.4, 0.3, 0.2]  # time delay in seconds between movements
		self.speed_time_delay = self.speed_time_delay_list[self.speed_time_delay_index]
		
		self.is_3d = is_3d
		
		self.last_motion_step_time = datetime.now()
		# self.board_reset_time = datetime.now() + timedelta(seconds=3.5)
		self.board_reset_time = None
		self.enable_gameplay_time = datetime.now() + timedelta(seconds=6)
		self.is_gameplay_enabled = False
		
		self.direction = 'right'
		self.next_direction = None
		
		self.snake = []  # ordered array of pixels that are part of the snake
		self.target = 0, 0, 0  # the pixel to be eaten
		
	@classmethod
	def create_new(cls, existing, light_dimensions):
		if len(existing.snake) > 1:
			# we want to make a new game but keep the snake length the same
			# this could happen when switching between 2D and 3D or when the lights get reallocated
			# the challenge is deciding where to draw the snake since its original location may not be available any more after light reallocation
			pass
			
		return cls(
			existing.logger,
			light_dimensions,
			existing.light_sender,
			gui=existing.gui, 
			is_3d=existing.is_3d,
			speed_time_delay_index=existing.speed_time_delay_index
		)
		
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
		
	def set_direction(self, next_direction):
		# update the current direction if it is valid for the 3Dness and if it isn't a 180 degree turn from current
		# using 2 variables to avoid multiple inputs between movements that accidentally allow the snake to do a 180 degree turn and run into itself
		if next_direction in self.get_direction_list():
			if next_direction != self.get_opposite_direction(self.direction):
				self.next_direction = next_direction
			
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
		L, H, D = self.light_dimensions
		pulse_plans = []
		packet = None
		draw_packet = False
		
		# assess timer to see if a new board should be drawn
		if self.board_reset_time is not None and (current_time - self.board_reset_time).total_seconds() > 0:
			self.logger.info(f'Creating new Snake gameboard since time of {self.board_reset_time} has been reached')
			self.board_reset_time = None
			pulse_plans += self.make_new_game(include_intro_screen=False)
			draw_packet = True
		
		# assess timer to see if gameplay should be re-enabled
		if not self.is_gameplay_enabled and self.enable_gameplay_time is not None and (current_time - self.enable_gameplay_time).total_seconds() > 0:
			self.logger.info(f'Enabling Snake gameplay since time of {self.enable_gameplay_time} has been reached')
			self.enable_gameplay_time = None
			self.is_gameplay_enabled = True
			draw_packet = True
		
		if self.is_gameplay_enabled and (current_time - self.last_motion_step_time).total_seconds() >= self.speed_time_delay:
			hit_boundary, hit_self, hit_target = self.move_one_step()
			self.last_motion_step_time = current_time
			draw_packet = True

			# first flash the score (length of snake) "SCORE" in white stacked above number in green (perhaps 3 seconds long)
			# then create the new board but don't start yet
			# give a quick 3, 2, 1, GO message before starting the snake movement (2 seconds total) (this happens in the make_new_board function
			# that whole thing can be a single temp packet plan, but it needs to be treated as blocking while it exists
			# ideally the board (main packet plan?) would reset after the score is flashed but before the countdown
			# since snake game doesn't actually track its own temp plans, better answer is to just track a boolean for the duration of time
			# we know that plan will be running that tells us not to actually play the game
			# Once that time elapses, the boolean is toggled and game play begins again
			# We can set a different variable to know when to reset the board so it happens at the right time in the middle

			# if hit boundary/self, pulse red/orange and prepare to start the game over by showing the score
			if hit_boundary or hit_self:
				color = 'red' if hit_boundary else 'orange'
				game_over_pulse_plan = PacketPlan(
					Lights.make_pulse_packet_time_series(light_dimensions=self.light_dimensions, color_rgb=Lights.rgb_from_color(color), frames=6), 
					time_delay=0.05
				)
				score = len(self.snake)
				self.logger.info(f"Snake game ended with hit_boundary[{hit_boundary}] and hit_self[{hit_self}] with score of {score}")
										
				if L == 30:
					letters = ["     ", "s", " ", "c", " ", "o", " ", "r", " ", "e"]
					colors = ["white"] * len(letters)
					score_color = "green"
				elif L == 15:
					letters = ["s", "c", "o", "r", "e"]
					colors = ["red", "green", "red", "green", "red"]
					score_color = "white"
				else:
					# L == 10 or possibly as low as 5 if there are 4 controllers on a 20 wide display
					letters = []
					colors = []
					score_color = "white"
					
				# make the score message plan
				overlay_grid = [[] for h in range(H)]
				pixels_used = Lights.get_cols_used_for_number(num_digits=len(str(score)), width="narrow")
				front_pad = int(int(L - pixels_used) / int(2))
				number_grids = [Lights.make_letter(" " * front_pad)]
				for digit in str(score):
					number_grids.append(Lights.make_number(int(digit), width="narrow", color=score_color))
					number_grids.append(Lights.make_letter(" "))
				number_grids.pop()  # remove the last item since it's an unwanted trailing space
				
				for number_grid in number_grids:
					for i, row in enumerate(number_grid):
						overlay_grid[i] += row
					
				letter_grids = [Lights.make_letter(letter, width="narrow", color=colors[i]) for i, letter in enumerate(letters)]
				for letter_grid in letter_grids:
					for i, row in enumerate(letter_grid):
						overlay_grid[i+5] += row
				
				packet = Lights.make_blackout_packet(self.light_dimensions)
				for j, row in enumerate(overlay_grid):
					for i, pixel in enumerate(row):
						if pixel != (0, 0, 0):
							try:
								packet[0][j][i] = pixel
							except IndexError:
								# if we somehow have more to map than exists in our allocated display, just log it and skip that item
								# this could happen if the score is high and the display is really small
								print('overlay grid dimension exceeds size of packet')
				
				print("length game over pulse plan before adding score", len(game_over_pulse_plan.packet_time_series))
				score_packet_time_series = [packet for x in range(25)]
				game_over_pulse_plan.packet_time_series += score_packet_time_series
				print("length game over pulse plan after adding score", len(game_over_pulse_plan.packet_time_series))
				# game_over_pulse_plan.validate_packet_time_series(self.light_dimensions)
				pulse_plans.append(game_over_pulse_plan)
				
				self.is_gameplay_enabled = False
				self.enable_gameplay_time = current_time + timedelta(seconds=6)
				self.board_reset_time = current_time + timedelta(seconds=3.5)
				draw_packet = False
				packet = Lights.make_blackout_packet(self.light_dimensions)
				
			# if caught the next bite, quick pulse green and make a new target
			elif hit_target:
				pulse_plans.append(
					PacketPlan(
						Lights.make_pulse_packet_time_series(light_dimensions=self.light_dimensions, color_rgb=Lights.rgb_from_color('green'), frames=3), 
						time_delay=0.05
					)
				)
				self.target = self.make_target()
				
		if draw_packet:
			# if we just moved without hitting anything or ate the target, then redraw the board
			# otherwise, we want the board to stay the same because either nothing has changed
			# or we just lost and want to wait a few seconds before redrawing the board anyway,
			# which will happen based on a timer
			packet = self.draw_game_board()
		
		return packet, pulse_plans
		
	def move_one_step(self):
		L, H, D = self.light_dimensions
		x, y, z = self.snake[0]
		
		hit_boundary = False
		hit_self = False
		hit_target = False
				
		# first move the snake and verify it doesn't hit a wall
		if self.next_direction is not None:
			self.direction = self.next_direction
			self.next_direction = None
		
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
		
		num_pixels = L * H * D
		if len(self.snake) >= num_pixels:
			self.logger.warning('Existing snake is bigger than the available number of pixels. Starting a new game')
			self.snake = (0, 0, 0)
			
		target = self.snake[0]
		while target in self.snake:
			target = (random.randrange(0, L), random.randrange(0, H), random.randrange(0, D))
			
		return target
		
	def redraw_existing_snake(self, snake_length):
		L, H, D = self.light_dimensions
		if not self.is_3d:
			D = 1		
		
		moving_right = False
		y = -1
		z = 0
		temp_snake = []
		for i in range(snake_length):
			# go left to right along bottom
			# then go up one row and go right to left
			mod_i = (i) % L
			if mod_i == 0:
				y += 1
				moving_right = not moving_right
			
			if moving_right:
				x = mod_i
			else:
				x = (L - mod_i - 1)
				
			temp_snake.append((x, y, z))
			
		temp_snake.reverse()
		
		if y < H:
			direction = 'up'
		else:
			if moving_right:
				direction = 'right'
			else:
				direction = 'left'
		
		return temp_snake, direction
		
	def make_new_game(self, starting_snake_length=None, include_intro_screen=True):
		L, H, D = self.light_dimensions
		self.logger.info(f"Creating new Snake game with starting_snake_length[{starting_snake_length}] and include_intro_screen[{include_intro_screen}]")
		
		if not self.is_3d:
			D = 1
		num_pixels = L * H * D
		
		if starting_snake_length is None:
			# pick an initial spot for the snake to start at the front, bottom, left corner and have it moving to the right
			self.snake = [(0,0,0)]
			self.direction = 'right'
		elif starting_snake_length >= num_pixels:
			self.logger.warning('Existing snake is bigger than the available number of pixels. Starting a new game')
			
			# pick an initial spot for the snake to start at the front, bottom, left corner and have it moving to the right
			self.snake = [(0,0,0)]
			self.direction = 'right'
		else:
			# we want to redraw an existing snake due to reallocation. Just draw it snaking back and forth along the bottom front of the display.
			try:
				self.snake, self.direction = self.redraw_existing_snake(starting_snake_length)
			except Exception:
				self.logger.error('Encountered error trying to persist existing snake across reallocation. Starting a new game')
				self.snake = [(0,0,0)]
				self.direction = 'right'
				
		self.next_direction = None

		# pick an initial spot for the target
		self.target = self.make_target()
	
		pulse_plan = PacketPlan(time_delay=0.05)

		# make the "SNAKE" title screen and output it as a pulse plan
		if include_intro_screen:
			packet = Lights.make_blackout_packet(self.light_dimensions)
			overlay_grid = [[] for h in range(H)]
			if L == 30:
				letters = ["     ", "s", " ", "n", " ", "a", " ", "k", " ", "e"]
				colors = ["green"] * len(letters)
			elif L == 15:
				letters = ["s", "n", "a", "k", "e"]
				colors = ["green", "yellow", "green", "yellow", "green"]
			else:
				# L == 10 or possibly as low as 5 if there are 4 controllers on a 20 wide display
				letters = ["s"]
				colors = ["green"]
				
			letter_grids = [Lights.make_letter(letter, width="narrow", color=colors[i]) for i, letter in enumerate(letters)]
			for letter_grid in letter_grids:
				for i, row in enumerate(letter_grid):
					overlay_grid[i+5] += row
					
			for j, row in enumerate(overlay_grid):
				for i, pixel in enumerate(row):
					if pixel != (0, 0, 0):
						try:
							packet[0][j][i] = pixel
						except IndexError:
							# if we somehow have more to map than exists in our allocated display, just log it and skip that item
							# this could happen if the score is high and the display is really small
							print('overlay grid dimension exceeds size of packet')
			
			pulse_plan.packet_time_series += [packet for x in range(60)]
			
		# make the 3, 2, 1, GO countdown and output it as a pulse plan		
		for n in [3, 2, 1]:
			packet = Lights.make_blackout_packet(self.light_dimensions)
			overlay_grid = [[] for h in range(H)]
			pixels_used = Lights.get_cols_used_for_number(num_digits=len(str(n)), width="narrow")
			front_pad = int(int(L - pixels_used) / int(2))
			number_grids = [Lights.make_letter(" " * front_pad)]
			number_grids.append(Lights.make_number(int(n), width="narrow", color="white"))
			
			for number_grid in number_grids:
				for j, row in enumerate(number_grid):
					overlay_grid[j+5] += row
			
			for j, row in enumerate(overlay_grid):
				for i, pixel in enumerate(row):
					if pixel != (0, 0, 0):
						try:
							packet[0][j][i] = pixel
						except IndexError:
							# if we somehow have more to map than exists in our allocated display, just log it and skip that item
							# this could happen if the score is high and the display is really small
							print('overlay grid dimension exceeds size of packet')
			
			pts = Lights.make_pulse_packet_time_series(light_dimensions=self.light_dimensions, packet=packet, frames=7)
			pulse_plan.packet_time_series += pts
		
		# pulse_plan.validate_packet_time_series(self.light_dimensions)
			
		packet = Lights.make_blackout_packet(self.light_dimensions)
		overlay_grid = [[] for h in range(H)]
		if L >= 15:
			width = "wide"
			pixels_used = 11
		else:
			width = "narrow"
			pixels_used = 7
		
		letters = ["g", " ", "o"]
		front_pad = int(int(L - pixels_used) / int(2))
		grids = [Lights.make_letter(" " * front_pad)] + [Lights.make_letter(letter, width=width, color="green") for i, letter in enumerate(letters)]
		# print(grids)
		for letter_grid in grids:
			for j, row in enumerate(letter_grid):
				overlay_grid[j+5] += row
				
		# print(overlay_grid)
		
		for j, row in enumerate(overlay_grid):
			for i, pixel in enumerate(row):
				if pixel != (0, 0, 0):
					try:
						packet[0][j][i] = pixel
					except IndexError:
						# if we somehow have more to map than exists in our allocated display, just log it and skip that item
						# this could happen if the score is high and the display is really small
						print('overlay grid dimension exceeds size of packet')
						
		pts = Lights.make_pulse_packet_time_series(light_dimensions=self.light_dimensions, packet=packet, frames=7)
		pulse_plan.packet_time_series += pts
		print("length pulse plan packet time series", len(pulse_plan.packet_time_series))
		# pulse_plan.validate_packet_time_series(self.light_dimensions)
		return [pulse_plan]
		
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
		
	
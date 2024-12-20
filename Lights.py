from random import randint
from copy import deepcopy


class Lights:
	COLOR_LIST = ["green", "red", "yellow", "blue", "orange", "white", "black", "purple", "pink", "teal"]
	# packet plan is a 4 dimensional array
	# Time array around LxWxD around LxW around L
	# row, grid, packet, packet_plan
	# origin is front bottom left corner
	
	@staticmethod
	def make_blackout_packet(light_dimensions):
		L, H, D = light_dimensions
		return [[[(0, 0, 0) for i in range(L)] for j in range(H)] for k in range(D)]
	
	@staticmethod
	def rgb_from_color(color_name):
		if color_name == 'green':
			return 0, 255, 0
		elif color_name == 'red':
			return 255, 0, 0
		elif color_name == 'yellow':
			return 225, 200, 0
		elif color_name == 'blue':
			return 0, 0, 255
		elif color_name == 'orange':
			return 255, 100, 0
		elif color_name in ['neck', 'white']:
			return 255, 255, 255
		elif color_name == 'pink':
			return 255, 0, 255
		elif color_name == 'teal':
			return 0, 255, 255
		elif color_name == 'purple':
			return 100, 0, 255
		else:
			return 0, 0, 0
	
	@staticmethod
	def get_gradient_cutoffs(delta, num_sections):
		step = int(delta / num_sections)
		step_array = [step] * (num_sections - 1)
		# add_ind = 0
		# while sum(step_array) < delta:
			# step_array[add_ind] += 1
			# add_ind += 1
					
		# now generate the actual cutoff points for each
		color_vals = []
		for i, val in enumerate(step_array):
			color_vals.append(sum(step_array[:i+1]))
		
		return color_vals
	
	@staticmethod
	def make_gradient_colors(num_pixels, start_color, end_color):
		colors = []
		if num_pixels == 1:
			colors.append(start_color)
			
		elif num_pixels == 2:
			colors.append(start_color)
			colors.append(end_color)
			
		else:
			r1, g1, b1 = start_color
			r2, g2, b2 = end_color
			r_vals = Lights.get_gradient_cutoffs(r2 - r1, num_pixels - 1)
			g_vals = Lights.get_gradient_cutoffs(g2 - g1, num_pixels - 1)
			b_vals = Lights.get_gradient_cutoffs(b2 - b1, num_pixels - 1)
			
			colors.append(start_color)
			for i in range(len(r_vals)):
				item = r1 + r_vals[i], g1 + g_vals[i], b1 + b_vals[i]
				colors.append(item)
			colors.append(end_color)
				
		return colors
			
	@staticmethod
	def make_wipe_time_series(packet, direction):
		# get packet dimensions
		D = len(packet)
		H = len(packet[0])
		L = len(packet[0][0])
		
		packets = []
		
		if direction in ['right', 'left'] and L > 1:
			for i in range(L+1):
				packets.append(Lights.sub_packet(packet, i, direction))
			
			for i in range(L-1, 0, -1):
				packets.append(Lights.sub_packet(packet, i, direction))

		elif direction in ['up', 'down'] and H > 1:
			for i in range(H+1):
				packets.append(Lights.sub_packet(packet, i, direction))
			
			for i in range(H-1, 0, -1):
				packets.append(Lights.sub_packet(packet, i, direction))
				
		if direction in ['forward', 'backward'] and D > 1:
			for i in range(D+1):
				packets.append(Lights.sub_packet(packet, i, direction))
			
			for i in range(D-1, 0, -1):
				packets.append(Lights.sub_packet(packet, i, direction))
				
		return packets
			
	
	@staticmethod
	def shift_packet(packet, pixels_to_shift, right=False, left=False, up=False, down=False, forward=False, backward=False):
		if pixels_to_shift == 0:
			return packet
			
		# get packet dimensions
		D = len(packet)
		H = len(packet[0])
		L = len(packet[0][0])
								
		# left right is easiest since packet structure is laid out best for that
		if right or left and L > 1:
			pixels_to_shift_L = pixels_to_shift % L if pixels_to_shift >= L else pixels_to_shift
			num = -1 * pixels_to_shift_L if right else pixels_to_shift_L
			
			new_packet = []
			for grid in packet:
				new_grid = []
				for row in grid:
					new_grid.append(row[num:] + row[:num])
				new_packet.append(new_grid)
			packet = new_packet
		
		# for up down shifting, need to rearrange each grid to do the shift
		if up or down and H > 1:
			pixels_to_shift_H = pixels_to_shift % H if pixels_to_shift >= H else pixels_to_shift
			num = -1 * pixels_to_shift_H if up else pixels_to_shift_H
			
			'''
			init = [
				[A, B, C, D, E, F],
				[G, H, I, J, K, L],
				[M, N, O, P, Q, R],
				[S, T, U, V, W, X]			
			]
			
			trans = [
				[A, G, M, S],
				[B, H, N, T],
				[C, I, O, U],
				[D, J, P, V],
				[E, K, Q, W],
				[F, L, R, X]
			]
			
			shifted = [
				[G, M, S, A],
				[H, N, T, B],
				[I, O, U, C],
				[J, P, V, D],
				[K, Q, W, E],
				[L, R, X, F]
			]
			'''
			
			new_packet = []
			for grid in packet:
				t_grid = []		# H x L
				new_grid = []
				for x in range(L):
					t_col = [row[x] for row in grid]
					shifted = t_col[num:] + t_col[:num]
					t_grid.append(shifted)
				
				for x in range(H):
					row = [t_col[x] for t_col in t_grid]
					new_grid.append(row)
				new_packet.append(new_grid)
			packet = new_packet
				
			
		# for forward backward shifting, need to completely rearrange the whole packet to do the shift
		if forward or backward and D > 1:
			pixels_to_shift_D = pixels_to_shift % D if pixels_to_shift >= D else pixels_to_shift
			num = -1 * pixels_to_shift_D if forward else pixels_to_shift_D
			
			new_packet = []
			t_packet = []	# L x H x D
			for x in range(L):
				t_slice = []	# list of line lists
				for h in range(H):
					t_line = [packet[d][h][x] for d in range(D)]
					shifted = t_line[num:] + t_line[:num]
					t_slice.append(shifted)
				t_packet.append(t_slice)
		
			for d in range(D):
				new_grid = []
				for h in range(H):
					new_row = [t_packet[x][h][d] for x in range(L)]
					new_grid.append(new_row)
				new_packet.append(new_grid)
			packet = new_packet
		
		return packet
		
		
	@staticmethod
	def sub_packet(packet, num_pixels, direction):		
		# get packet dimensions
		D = len(packet)
		H = len(packet[0])
		L = len(packet[0][0])
		
		new_packet = []
		if direction in ['left', 'right']:
			for grid in packet:
				new_grid = []
				for row in grid:
					if direction == 'right':
						num = num_pixels
						new_grid.append(row[:num] + [(0, 0, 0) for _ in range(num, len(row) + 1)])
					else:
						num = L - num_pixels
						new_grid.append([(0, 0, 0) for _ in range(0, num)] + row[num:])
				new_packet.append(new_grid)
							
		elif direction in ['up', 'down']:
			for grid in packet:
				t_grid = []		# H x L
				new_grid = []
				for x in range(L):
					t_col = [row[x] for row in grid]
					if direction == 'up':
						num = num_pixels
						wipe_t_col = t_col[:num] + [(0, 0, 0) for _ in range(num, len(t_col) + 1)]
					else:
						num = H - num_pixels
						wipe_t_col = [(0, 0, 0) for _ in range(0, num)] + t_col[num:]
					
					t_grid.append(wipe_t_col)
				
				for x in range(H):
					row = [t_col[x] for t_col in t_grid]
					new_grid.append(row)
				new_packet.append(new_grid)
				
		elif direction in ['forward', 'backward']:
			t_packet = []	# L x H x D
			for x in range(L):
				t_slice = []	# list of line lists
				for h in range(H):
					t_line = [packet[d][h][x] for d in range(D)]
					if direction == 'forward':
						num = num_pixels
						wipe_t_line = t_line[:num] + [(0, 0, 0) for _ in range(num, len(t_line) + 1)]
					else:
						num = D - num_pixels
						wipe_t_line = [(0, 0, 0) for _ in range(0, num)] + t_line[num:]
					t_slice.append(wipe_t_line)
				t_packet.append(t_slice)
		
			for d in range(D):
				new_grid = []
				for h in range(H):
					new_row = [t_packet[x][h][d] for x in range(L)]
					new_grid.append(new_row)
				new_packet.append(new_grid)
		
		return new_packet
			
	@staticmethod
	def get_alternating_packet(colors_rgb, light_dimensions, segment_size=1):
		# make alternating grid in all dimensions alternating through the provided colors
		# work in 1D first to make a base row
		# then make additional rows using that first row with the appropriate offset to make the rest of the rows in the grid
		# then take that grid and shift it with the appropriate offset to make the rest of the grids in the packet
		L, H, D = light_dimensions
		num_colors = len(colors_rgb)
		
		# make the first row
		color_index = 0
		segment_index = 0
		row = []
		for i in range(L):
			row.append(colors_rgb[color_index])
			if segment_index == segment_size - 1:
				segment_index = 0
				color_index = 0 if color_index == num_colors - 1 else color_index + 1
			else:
				segment_index += 1
				
		# construct the first grid
		grid = []
		for i in range(H):
			shifted = Lights.shift_packet([[row]], i * segment_size, left=True)[0][0]
			grid.append(shifted)

		# construct the full packet
		packet = []
		for i in range(D):
			shifted = Lights.shift_packet([grid], i * segment_size, left=True)[0]
			packet.append(shifted)
			
		return packet
		
	@staticmethod
	def get_blocks_row(colors_rgb, L):
		num_colors = len(colors_rgb)
		section_size = round(L / num_colors)
		row = []
		color_index = 0
		section_index = 0
		for i in range(L):
			row.append(colors_rgb[color_index])
			if section_index == section_size - 1:
				section_index = 0
				color_index = min(color_index + 1, num_colors - 1)
			else:
				section_index += 1
				
		return row
		
	@staticmethod
	def get_blocks_grid(colors_rgb, L, H):
		num_colors = len(colors_rgb)
		section_size = round(H / num_colors)
		
		new_colors_rgb = list(colors_rgb)
		
		section_index = 0
		grid = []
		for i in range(H):
			grid.append(Lights.get_blocks_row(new_colors_rgb, L))
			if section_index == section_size - 1:
				section_index = 0
				new_colors_rgb = new_colors_rgb[1:] + new_colors_rgb[:1]
			else:
				section_index += 1
		
		return grid
		
	@staticmethod
	def get_blocks_packet(colors_rgb, light_dimensions):
		# the whole light string alternates statically with each color that was pressed, section by section
		# need to determine how many sections are needed across the string and determine the boundary points
		# need to determine this for all three axes independently based on their dimensions
		L, H, D = light_dimensions
		num_colors = len(colors_rgb)
		section_size = round(D / num_colors)

		# take the first row and replicate it section_size number of times
		# then calculate a shifted version of the row by changing the color ordering
		# (can't just truly shift the row because we don't know for sure that there aren't trailing dark pixels at the ends
		# due to the math not working out evenly
		new_colors_rgb = list(colors_rgb)
		
		section_index = 0
		packet = []
		for i in range(D):
			packet.append(Lights.get_blocks_grid(new_colors_rgb, L, H))
			if section_index == section_size - 1:
				section_index = 0
				new_colors_rgb = new_colors_rgb[1:] + new_colors_rgb[:1]
			else:
				section_index += 1
		
		return packet
		
	@staticmethod
	def make_pulse_packet_time_series(light_dimensions, packet=None, color_rgb=None, frames=11):
		if packet is None:
			packet = Lights.make_whole_string_packet(color_rgb, light_dimensions)
		base_time_series = [packet for x in range(frames)]
		pulse_levels = [1 - (1 / frames) * x for x in range(frames)]
		pulse_time_series = [Lights.make_scale_packet(x, light_dimensions) for x in pulse_levels]
		packet_time_series = Lights.apply_dim_time_series(base_time_series, pulse_time_series)
		
		return packet_time_series
		
	@staticmethod
	def make_meteor_packet_time_series(color_rgb, light_dimensions, start_pixel, frames=8, pulse_size=None):
		base_time_series = [Lights.make_whole_string_packet(color_rgb, light_dimensions) for _ in range(frames)]
		L, H, D = L1, H1, D1 = light_dimensions
		left = right = up = down = forward = backward = False
		
		x, y, z = start_pixel
		if x == 0 and y == 0 and z == 0:
			# front/bottom/left corner
			right = up = forward = True
		elif x == L - 1 and y == 0 and z == 0:
			# front/bottom/right corner
			left = up = forward = True
		elif x == L - 1 and y == H - 1 and z == 0:
			# front/top/right corner
			left = down = forward = True
		elif x == 0 and y == H - 1 and z == 0:
			# front/top/left corner
			right = down = forward = True
		elif x == 0 and y == 0 and z == D - 1:
			# back/bottom/left corner
			right = up = backward = True
		elif x == L - 1 and y == 0 and z == D - 1:
			# back/bottom/right corner 
			left = up = backward = True
		elif x == L - 1 and y == H - 1 and z == D - 1:
			# back/top/right corner
			left = down = backward = True
		elif x == 0 and y == H - 1 and z == D - 1:
			# back/top/left corner
			right = down = backward = True

		else:
			# starting from somewhere in the middle so wipe will go outward in all directions
			# spread speed determined by the larger gap in each axis
			L1 = max(x-0, L-1-x)
			H1 = max(y-0, H-1-y)
			D1 = max(z-0, D-1-z)
			left = right = up = down = forward = backward = True
		
		# make a packet of all zeros
		base_wipe_packet = Lights.make_scale_packet(0, light_dimensions)
		
		wipe_time_series = []
		for f in range(frames):
			# print(f"f = {f}")
			L_step = int(f * L1 / frames) + 1
			H_step = int(f * H1 / frames) + 1
			D_step = int(f * D1 / frames) + 1
			if pulse_size is not None:
				L_start = max(L_step - pulse_size, 0)
				H_start = max(H_step - pulse_size, 0)
				D_start = max(D_step - pulse_size, 0)
			else:
				L_start = H_start = D_start = 0
			# print(L_step, H_step, D_step)
			
			packet = deepcopy(base_wipe_packet)
	
			for i in range(D_start, D_step):
				# print(f"i = {i}")
				d_vals = []
				if forward:
					d_vals.append(z+i)
				if backward:
					d_vals.append(z-i)
					
				for j in range(H_start, H_step):
					# print(f"j = {j}")
					h_vals = []
					if up:
						h_vals.append(y+j)
					if down:
						h_vals.append(y-j)
						
					for k in range(L_start, L_step):
						# print(f"k = {k}")
						l_vals = []
						if right:
							l_vals.append(x+k)
						if left:
							l_vals.append(x-k)
							
						# print(d_vals, h_vals, l_vals)
						for dv in d_vals:
							for hv in h_vals:
								for lv in l_vals:
									try:
										packet[dv][hv][lv] = 1.0
									except IndexError:
										print("IndexError: ", dv, hv, lv)
										# raise
						
			wipe_time_series.append(packet)
			
		packet_time_series = Lights.apply_dim_time_series(base_time_series, wipe_time_series)
		
		return packet_time_series
		
	@staticmethod
	def apply_dim_time_series(packet_time_series, dim_time_series):
		final_time_series = []
		for i, packet in enumerate(packet_time_series):
			dim_packet = dim_time_series[i]
			final_packet = []
			for j, grid in enumerate(packet):
				dim_grid = dim_packet[j]
				final_grid = []
				for k, row in enumerate(grid):
					dim_row = dim_grid[k]
					final_row = [(int(a[0]*b), int(a[1]*b), int(a[2]*b)) for a,b in zip(row, dim_row)]
					final_grid.append(final_row)
				final_packet.append(final_grid)
			final_time_series.append(final_packet)
					
		return final_time_series
		
	@staticmethod
	def merge_packets(packets, light_dimensions):
		# adds together the individual elements of all the provided packets
		L, H, D = light_dimensions
		new_packet = []
		for i in range(D):
			grid = []
			for j in range(H):
				row = []
				for k in range(L):
					pixels = [packet[i][j][k] for packet in packets]
					try:
						r = min(sum([x[0] for x in pixels]), 255)
						g = min(sum([x[1] for x in pixels]), 255)
						b = min(sum([x[2] for x in pixels]), 255)
						row.append((r,g,b))
					except TypeError:
						print(pixels)
						for packet in packets:
							print(packet[0])
						raise
				grid.append(row)
			new_packet.append(grid)
			
		return new_packet
	
	@staticmethod
	def make_rainbow_row(num_pixels, color_shift=0):
		colors = ["red", "orange", "yellow", "green", "blue", "purple"]
		new_colors = colors[color_shift:] + colors[:color_shift]
		colors_rgb = [Lights.rgb_from_color(x) for x in new_colors]
		packet = Lights.get_blocks_row(colors_rgb, num_pixels)
		return packet
		
	@staticmethod
	def make_interlude_packet_time_series(light_dimensions):
		# rainbow blocks scrolling one direction at 10% dimming
		# a full brightness hot spot scrolling the other direction at a different speed
		# 3x around for dimming while only 1x around for rainbow
		L, H, D = light_dimensions
		
		# make a base rainbow packet for each row in the matrix
		packet = []
		for k in range(D):
			grid = []
			for j in range(H):
				grid.append(Lights.make_rainbow_row(L, color_shift=randint(0, 6)))
			packet.append(grid)
		
		# make the full packet_plan at full brightness
		packet_time_series = []
		for i in range(L):
			new_packet = []
			for grid in packet:
				new_grid = []
				for row in grid:
					new_row = Lights.shift_packet([[row]], i, left=True)[0][0]
					new_grid.append(new_row)
				new_packet.append(new_grid)
			packet_time_series.append(new_packet)
			packet_time_series.append(new_packet)
			packet_time_series.append(new_packet)
				
		# make the base dimming packet
		dim_packet = []
		for k in range(D):
			dim_grid = []
			for j in range(H):
				for i in range(L):
					start_index = randint(0, L - 5)
					stop_index = start_index + 5
					dim_row = [0.1] * L
					dim_row[start_index:stop_index] = [0.7, 0.85, 1.0, 0.85, 0.7]
					dim_grid.append(dim_row)
			dim_packet.append(dim_grid)
					
		# propagate the dim_packet for every timestep
		dim_time_series = []
		for i in range(len(packet_time_series)):
			new_dim_packet = []
			for dim_grid in dim_packet:
				new_dim_grid = []
				for dim_row in dim_grid:
					new_dim_row = Lights.shift_packet([[dim_row]], i, right=True)[0][0]
					new_dim_grid.append(new_dim_row)
				new_dim_packet.append(new_dim_grid)
			dim_time_series.append(new_dim_packet)
		
		# multiply the packet_plan by the dim_plan to get the final result
		final_time_series = Lights.apply_dim_time_series(packet_time_series, dim_time_series)
		
		# add in a text overlay on the interlude front grid
		overlay_grid = [[] for h in range(H)]
		if L == 10:
			pass
		elif L == 20:
			# overlay the stacked "COME PLAY" message across the top
			letters = ["c", " ", "o", " ", "m", " ", "e"]
			letter_grids = [Lights.make_letter(letter, color="white") for letter in letters]
			
			for letter_grid in letter_grids:
				for i, row in enumerate(letter_grid):
					overlay_grid[i] += row
					
			letters = ["p", " ", "l", " ", "a", " ", "y"]
			letter_grids = [Lights.make_letter(letter) for letter in letters]
			
			for letter_grid in letter_grids:
				for i, row in enumerate(letter_grid):
					overlay_grid[i+5] += row
			
		elif L == 30:				
			# overlay stacked "COME PLAY" message with wide letters in red and green
			letters = [" ", "p", "  ", "l", "   ", "a", "   ", "y"]
			letter_grids = [Lights.make_letter(letter, width="wide", color="green") for letter in letters]
			for letter_grid in letter_grids:
				for i, row in enumerate(letter_grid):
					overlay_grid[i] += row
					
			letters = [" ", "c", "  ", "o", "   ", "m", "   ", "e"]
			letter_grids = [Lights.make_letter(letter, width="wide", color="red") for letter in letters]
			for letter_grid in letter_grids:
				for i, row in enumerate(letter_grid):
					overlay_grid[i+5] += row
			
		if overlay_grid:
			for packet in final_time_series:
				# erase the first grid
				for j, row in enumerate(packet[0]):
					for i, pixel in enumerate(row):
						packet[0][j][i] = (0, 0, 0)
						
				# add the overlay
				for j, row in enumerate(overlay_grid):
					for i, pixel in enumerate(row):
						if pixel != (0, 0, 0):
							try:
								packet[0][j][i] = pixel
							except Exception:
								print(i, j)
								raise
		
		return final_time_series
		
	@staticmethod
	def make_scale_packet(scale_value, light_dimensions):
		L, H, D = light_dimensions
		packet = []
		for i in range(D):
			grid = []
			for j in range(H):
				row = [scale_value for k in range(L)]
				grid.append(row)
			packet.append(grid)
		
		return packet	
	
	@staticmethod
	def make_whole_string_packet(rgb, light_dimensions, scale_value=None):
		L, H, D = light_dimensions
		
		if scale_value is not None:
			rgb = (int(rgb[0]*scale_value), int(rgb[1]*scale_value), int(rgb[2]*scale_value))
		
		packet = []
		for i in range(D):
			grid = []
			for j in range(H):
				row = [rgb for k in range(L)]
				grid.append(row)
			packet.append(grid)
			
		return packet
		
	@staticmethod
	def make_number(number, width="narrow", color="white"):
		rgb_tuple = Lights.rgb_from_color(color)
		
		# defined as they look
		# when consuming, the rows are reversed automatically to account for
		# origin being at bottom left instead of top left
		
		wide_number_dict = {
			0: [
				[1, 1, 1, 1],
				[1, 0, 0, 1],
				[1, 0, 0, 1],
				[1, 0, 0, 1],
				[1, 1, 1, 1]
			],
			1: [
				[0, 1, 0, 0],
				[1, 1, 0, 0],
				[0, 1, 0, 0],
				[0, 1, 0, 0],
				[1, 1, 1, 0]
			],
			2: [
				[1, 1, 1, 1],
				[0, 0, 0, 1],
				[1, 1, 1, 1],
				[1, 0, 0, 0],
				[1, 1, 1, 1]
			],
			3: [
				[1, 1, 1, 1],
				[0, 0, 0, 1],
				[0, 1, 1, 1],
				[0, 0, 0, 1],
				[1, 1, 1, 1]
			],
			4: [
				[1, 0, 0, 1],
				[1, 0, 0, 1],
				[1, 1, 1, 1],
				[0, 0, 0, 1],
				[0, 0, 0, 1]
			],
			5: [
				[1, 1, 1, 1],
				[1, 0, 0, 0],
				[1, 1, 1, 1],
				[0, 0, 0, 1],
				[1, 1, 1, 1]
			],
			6: [
				[1, 0, 0, 0],
				[1, 0, 0, 0],
				[1, 1, 1, 1],
				[1, 0, 0, 1],
				[1, 1, 1, 1]
			],
			7: [
				[1, 1, 1, 1],
				[0, 0, 0, 1],
				[0, 0, 0, 1],
				[0, 0, 0, 1],
				[0, 0, 0, 1]
			],
			8: [
				[1, 1, 1, 1],
				[1, 0, 0, 1],
				[1, 1, 1, 1],
				[1, 0, 0, 1],
				[1, 1, 1, 1]
			],
			9: [
				[1, 1, 1, 1],
				[1, 0, 0, 1],
				[1, 1, 1, 1],
				[0, 0, 0, 1],
				[0, 0, 0, 1]
			],
		}
		
		narrow_number_dict = {
			0: [
				[1, 1, 1],
				[1, 0, 1],
				[1, 0, 1],
				[1, 0, 1],
				[1, 1, 1]
			],
			1: [
				[0, 1, 0],
				[1, 1, 0],
				[0, 1, 0],
				[0, 1, 0],
				[1, 1, 1]
			],
			2: [
				[1, 1, 1],
				[0, 0, 1],
				[1, 1, 1],
				[1, 0, 0],
				[1, 1, 1]
			],
			3: [
				[1, 1, 1],
				[0, 0, 1],
				[1, 1, 1],
				[0, 0, 1],
				[1, 1, 1]
			],
			4: [
				[1, 0, 1],
				[1, 0, 1],
				[1, 1, 1],
				[0, 0, 1],
				[0, 0, 1]
			],
			5: [
				[1, 1, 1],
				[1, 0, 0],
				[1, 1, 1],
				[0, 0, 1],
				[1, 1, 1]
			],
			6: [
				[1, 0, 0],
				[1, 0, 0],
				[1, 1, 1],
				[1, 0, 1],
				[1, 1, 1]
			],
			7: [
				[1, 1, 1],
				[0, 0, 1],
				[0, 0, 1],
				[0, 0, 1],
				[0, 0, 1]
			],
			8: [
				[1, 1, 1],
				[1, 0, 1],
				[1, 1, 1],
				[1, 0, 1],
				[1, 1, 1]
			],
			9: [
				[1, 1, 1],
				[1, 0, 1],
				[1, 1, 1],
				[0, 0, 1],
				[0, 0, 1]
			]
		}
		
		if width == 'narrow':
			item = narrow_number_dict[number]
		elif width == 'wide':
			item = wide_number_dict[number]
			
		return [[tuple(x*c for c in rgb_tuple) for x in row] for row in reversed(item)]
	
	@staticmethod
	def make_letter(letter, width='narrow', color="white"):
		rgb_tuple = Lights.rgb_from_color(color)
		
		space_array =  [
			[0],
			[0],
			[0],
			[0],
			[0]
		]
		
		# defined as they look
		# when consuming, the rows are reversed automatically to account for
		# origin being at bottom left instead of top left
		wide_letter_dict = {
			"a": [
				[0, 0, 1, 0, 0],
				[0, 1, 0, 1, 0],
				[0, 1, 0, 1, 0],
				[1, 1, 1, 1, 1],
				[1, 0, 0, 0, 1]
			],
			"b": [
				[1, 1, 1, 0, 0],
				[1, 0, 0, 1, 0],
				[1, 1, 1, 0, 0],
				[1, 0, 0, 1, 0],
				[1, 1, 1, 0, 0]
			],
			"c": [
				[0, 1, 1, 1, 0],
				[1, 0, 0, 0, 0],
				[1, 0, 0, 0, 0],
				[1, 0, 0, 0, 0],
				[0, 1, 1, 1, 0]
			],
			"d": [
				[1, 1, 1, 0, 0],
				[1, 0, 0, 1, 0],
				[1, 0, 0, 1, 0],
				[1, 0, 0, 1, 0],
				[1, 1, 1, 0, 0]
			],
			"e": [
				[1, 1, 1, 1, 0],
				[1, 0, 0, 0, 0],
				[1, 1, 1, 0, 0],
				[1, 0, 0, 0, 0],
				[1, 1, 1, 1, 0]
			],
			"f": [
				[1, 1, 1, 1, 0],
				[1, 0, 0, 0, 0],
				[1, 1, 1, 0, 0],
				[1, 0, 0, 0, 0],
				[1, 0, 0, 0, 0]
			],
			"g": [
				[0, 1, 1, 1, 0],
				[1, 0, 0, 0, 0],
				[1, 0, 0, 1, 1],
				[1, 0, 0, 0, 1],
				[0, 1, 1, 1, 0]
			],
			"h": [
				[1, 0, 0, 1, 0],
				[1, 0, 0, 1, 0],
				[1, 1, 1, 1, 0],
				[1, 0, 0, 1, 0],
				[1, 0, 0, 1, 0]
			],
			"i": [
				[1, 1, 1, 1, 1],
				[0, 0, 1, 0, 0],
				[0, 0, 1, 0, 0],
				[0, 0, 1, 0, 0],
				[1, 1, 1, 1, 1]
			],
			"j": [
				[0, 0, 0, 1, 0],
				[0, 0, 0, 1, 0],
				[0, 0, 0, 1, 0],
				[1, 0, 0, 1, 0],
				[0, 1, 1, 0, 0]
			],
			"k": [
				[1, 0, 0, 1, 0],
				[1, 0, 1, 0, 0],
				[1, 1, 0, 0, 0],
				[1, 0, 1, 0, 0],
				[1, 0, 0, 1, 0]
			],
			"l": [
				[1, 0, 0, 0, 0],
				[1, 0, 0, 0, 0],
				[1, 0, 0, 0, 0],
				[1, 0, 0, 0, 0],
				[1, 1, 1, 1, 0]
			],
			"m": [
				[1, 0, 0, 0, 1],
				[1, 1, 0, 1, 1],
				[1, 0, 1, 0, 1],
				[1, 0, 0, 0, 1],
				[1, 0, 0, 0, 1]
			],
			"n": [
				[1, 0, 0, 0, 1],
				[1, 1, 0, 0, 1],
				[1, 0, 1, 0, 1],
				[1, 0, 0, 1, 1],
				[1, 0, 0, 0, 1]
			],
			"o": [
				[0, 1, 1, 1, 0],
				[1, 0, 0, 0, 1],
				[1, 0, 0, 0, 1],
				[1, 0, 0, 0, 1],
				[0, 1, 1, 1, 0]
			],
			"p": [
				[1, 1, 1, 0, 0],
				[1, 0, 0, 1, 0],
				[1, 1, 1, 0, 0],
				[1, 0, 0, 0, 0],
				[1, 0, 0, 0, 0]
			],
			"q": [
				[0, 1, 1, 0, 0],
				[1, 0, 0, 1, 0],
				[1, 0, 0, 1, 0],
				[1, 0, 0, 1, 0],
				[0, 1, 1, 0, 1]
			],
			"r": [
				[1, 1, 1, 0, 0],
				[1, 0, 0, 1, 0],
				[1, 1, 1, 0, 0],
				[1, 0, 0, 1, 0],
				[1, 0, 0, 1, 0]
			],
			"s": [
				[0, 1, 1, 1, 0],
				[1, 0, 0, 0, 0],
				[0, 1, 1, 0, 0],
				[0, 0, 0, 1, 0],
				[1, 1, 1, 0, 0]
			],
			"t": [
				[1, 1, 1, 1, 1],
				[0, 0, 1, 0, 0],
				[0, 0, 1, 0, 0],
				[0, 0, 1, 0, 0],
				[0, 0, 1, 0, 0]
			],
			"u": [
				[1, 0, 0, 1, 0],
				[1, 0, 0, 1, 0],
				[1, 0, 0, 1, 0],
				[1, 0, 0, 1, 0],
				[0, 1, 1, 0, 0]
			],
			"v": [
				[1, 0, 0, 0, 1],
				[1, 0, 0, 0, 1],
				[0, 1, 0, 1, 0],
				[0, 1, 0, 1, 0],
				[0, 0, 1, 0, 0]
			],
			"w": [
				[1, 0, 0, 0, 1],
				[1, 0, 0, 0, 1],
				[1, 0, 1, 0, 1],
				[1, 1, 0, 1, 1],
				[1, 0, 0, 0, 1]
			],
			"x": [
				[1, 0, 0, 0, 1],
				[0, 1, 0, 1, 0],
				[0, 0, 1, 0, 0],
				[0, 1, 0, 1, 0],
				[1, 0, 0, 0, 1]
			],
			"y": [
				[1, 0, 0, 0, 1],
				[0, 1, 0, 1, 0],
				[0, 0, 1, 0, 0],
				[0, 0, 1, 0, 0],
				[0, 0, 1, 0, 0]
			],
			"z": [
				[1, 1, 1, 1, 1],
				[0, 0, 0, 1, 0],
				[0, 0, 1, 0, 0],
				[0, 1, 0, 0, 0],
				[1, 1, 1, 1, 1]
			]
		}
		narrow_letter_dict = {
			"a": [
				[0, 1, 0],
				[1, 0, 1],
				[1, 1, 1],
				[1, 0, 1],
				[1, 0, 1]
			],
			"b": [
				[1, 1, 0],
				[1, 0, 1],
				[1, 1, 0],
				[1, 0, 1],
				[1, 1, 0]
			],
			"c": [
				[0, 1, 1],
				[1, 0, 0],
				[1, 0, 0],
				[1, 0, 0],
				[0, 1, 1]
			],
			"d": [
				[1, 1, 0],
				[1, 0, 1],
				[1, 0, 1],
				[1, 0, 1],
				[1, 1, 0]
			],
			"e": [
				[1, 1, 1],
				[1, 0, 0],
				[1, 1, 0],
				[1, 0, 0],
				[1, 1, 1]
			],
			"f": [
				[1, 1, 1],
				[1, 0, 0],
				[1, 1, 0],
				[1, 0, 0],
				[1, 0, 0]
			],
			"g": [
				[0, 1, 1],
				[1, 0, 0],
				[1, 0, 0],
				[1, 0, 1],
				[0, 1, 1]
			],
			"h": [
				[1, 0, 1],
				[1, 0, 1],
				[1, 1, 1],
				[1, 0, 1],
				[1, 0, 1]
			],
			"i": [
				[1, 1, 1],
				[0, 1, 0],
				[0, 1, 0],
				[0, 1, 0],
				[1, 1, 1]
			],
			"j": [
				[0, 0, 1],
				[0, 0, 1],
				[0, 0, 1],
				[1, 0, 1],
				[0, 1, 0]
			],
			"k": [
				[1, 0, 1],
				[1, 0, 1],
				[1, 1, 0],
				[1, 0, 1],
				[1, 0, 1]
			],
			"l": [
				[1, 0, 0],
				[1, 0, 0],
				[1, 0, 0],
				[1, 0, 0],
				[1, 1, 1]
			],
			"m": [
				[1, 0, 1],
				[1, 1, 1],
				[1, 0, 1],
				[1, 0, 1],
				[1, 0, 1]
			],
			"n": [
				[1, 0, 1],
				[1, 1, 1],
				[1, 1, 1],
				[1, 1, 1],
				[1, 0, 1]
			],
			"o": [
				[0, 1, 0],
				[1, 0, 1],
				[1, 0, 1],
				[1, 0, 1],
				[0, 1, 0]
			],
			"p": [
				[1, 1, 0],
				[1, 0, 1],
				[1, 1, 0],
				[1, 0, 0],
				[1, 0, 0]
			],
			"q": [
				[0, 1, 0],
				[1, 0, 1],
				[1, 0, 1],
				[1, 0, 1],
				[0, 1, 1]
			],
			"r": [
				[1, 1, 0],
				[1, 0, 1],
				[1, 1, 0],
				[1, 0, 1],
				[1, 0, 1]
			],
			"s": [
				[0, 1, 1],
				[1, 0, 0],
				[0, 1, 0],
				[0, 0, 1],
				[1, 1, 0]
			],
			"t": [
				[1, 1, 1],
				[0, 1, 0],
				[0, 1, 0],
				[0, 1, 0],
				[0, 1, 0]
			],
			"u": [
				[1, 0, 1],
				[1, 0, 1],
				[1, 0, 1],
				[1, 0, 1],
				[1, 1, 1]
			],
			"v": [
				[1, 0, 1],
				[1, 0, 1],
				[1, 0, 1],
				[1, 0, 1],
				[0, 1, 0]
			],
			"w": [
				[1, 0, 1],
				[1, 0, 1],
				[1, 0, 1],
				[1, 1, 1],
				[1, 0, 1]
			],
			"x": [
				[1, 0, 1],
				[1, 0, 1],
				[0, 1, 0],
				[1, 0, 1],
				[1, 0, 1]
			],
			"y": [
				[1, 0, 1],
				[1, 0, 1],
				[0, 1, 0],
				[0, 1, 0],
				[0, 1, 0]
			],
			"z": [
				[1, 1, 1],
				[0, 0, 1],
				[0, 1, 0],
				[1, 0, 0],
				[1, 1, 1]
			]
		}
		
		if letter.strip() == '':
			# we just have one or more spaces
			num_spaces = len(letter)
			item = [num_spaces * x for x in space_array]
		
		else:
			if width == 'narrow':
				item = narrow_letter_dict[letter.lower()]
			elif width == 'wide':
				item = wide_letter_dict[letter.lower()]
			
			
		return [[tuple(x*c for c in rgb_tuple) for x in row] for row in reversed(item)]
		
	def get_cols_used_for_number(num_digits, width="narrow", inter_spaces=1):
		cols_per_digit = 3 if width == "narrow" else 4
		total = num_digits * cols_per_digit + (num_digits - 1) * inter_spaces
		
		return total
			
		
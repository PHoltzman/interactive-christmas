from random import randint

class Lights:
	COLOR_LIST = ["green", "red", "yellow", "blue", "orange", "white", "black", "purple", "pink", "teal"]
	# packet plan is a 4 dimensional array
	# Time array around LxWxD around LxW around L
	# row, grid, packet
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
			num = -1 * pixels_to_shift_H if down else pixels_to_shift_H
			
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
	def sub_packet(packet, num_pixels):
		# TODO: make this handle more than just scrolling in L direction
		num = num_pixels
		new_packet = []
		for grid in packet:
			new_grid = []
			for row in grid:
				new_grid.append(row[:num] + [(0, 0, 0) for x in range(num, len(row) + 1)])
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
	def make_rainbow_row(num_pixels, color_shift=0):
		colors = ["red", "orange", "yellow", "green", "blue", "purple"]
		colors_rgb = [Lights.rgb_from_color(x) for x in colors]
		packet = Lights.get_blocks_row(colors_rgb, num_pixels)
		return packet
		
	@staticmethod
	def make_interlude_packet_plan(light_dimensions):
		# rainbow blocks scrolling one direction at 50% dimming
		# a full brightness hot spot scrolling the other direction at a different speed
		# 3x around for dimming while only 1x around for rainbow
		L, H, D = light_dimensions
		
		# Limited to just 2D for now
		# make a base rainbow packet for each row in the matrix
		grid = []
		for j in range(H):
			grid.append(Lights.make_rainbow_row(L, color_shift=randint(0, 6)))
		packet = [grid]
		
		# make the full packet_plan at full brightness
		packet_plan = []
		for i in range(L):
			for grid in packet:
				new_grid = []
				for row in grid:
					new_row = Lights.shift_packet([[row]], i, left=True)[0][0]
					new_grid.append(new_row)
			new_packet = [new_grid]
			packet_plan.append(new_packet)
			packet_plan.append(new_packet)
			packet_plan.append(new_packet)
				
		# make the base dimming packet
		dim_grid = []
		for j in range(H):
			start_index = randint(0, L - 5)
			stop_index = start_index + 5
			dim_row = [0.1] * L
			dim_row[start_index:stop_index] = [0.7, 0.85, 1.0, 0.85, 0.7]
			dim_grid.append(dim_row)
		dim_packet = [dim_grid]
				
		# propagate the dim_packet for every timestep
		dim_plan = []
		for i in range(len(packet_plan)):
			for dim_grid in dim_packet:
				new_dim_grid = []
				for dim_row in dim_grid:
					new_dim_row = Lights.shift_packet([[dim_row]], i, right=True)[0][0]
					new_dim_grid.append(new_dim_row)
			new_dim_packet = [new_dim_grid]
			dim_plan.append(new_dim_packet)
		
		# multiply the packet_plan by the dim_plan to get the final result
		final_plan = []
		for i, packet in enumerate(packet_plan):
			dim_packet = dim_plan[i]
			final_packet = []
			for j, grid in enumerate(packet):
				dim_grid = dim_packet[j]
				final_grid = []
				for k, row in enumerate(grid):
					dim_row = dim_grid[k]
					# print(row)
					final_row = [(int(a[0]*b), int(a[1]*b), int(a[2]*b)) for a,b in zip(row, dim_row)]
					final_grid.append(final_row)
				final_packet.append(final_grid)
			final_plan.append(final_packet)
					
		return final_plan
		
	@staticmethod
	def make_whole_string_packet(r, g, b, light_dimensions):
		L, H, D = light_dimensions
		packet = []
		for i in range(D):
			grid = []
			for j in range(H):
				row = [(r, g, b) for k in range(L)]
				grid.append(row)
			packet.append(grid)
			
		return packet
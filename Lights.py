class Lights:
	COLOR_LIST = ["green", "red", "yellow", "blue", "orange", "white", "black", "purple", "pink", "teal"]
	
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
	def shift_packet(packet, pixels_to_shift, direction='right'):
		if pixels_to_shift == 0:
			return packet
			
		if direction == 'right':
			num = -3 * pixels_to_shift
			return packet[num:] + packet[:num]
			
		else:
			num = 3 * pixels_to_shift
			return packet[num:] + packet[:num]
			
	@staticmethod
	def sub_packet(packet, num_pixels):
		num = 3 *  num_pixels
		return packet[:num]

	@staticmethod
	def get_alternating_packet(colors_rgb, num_pixels, segment_size=1):
		num_colors = len(colors_rgb)
		packet = []
		color_index = 0
		segment_index = 0
		for i in range(num_pixels):
			packet += colors_rgb[color_index]
			if segment_index == segment_size - 1:
				segment_index = 0
				color_index = 0 if color_index == num_colors - 1 else color_index + 1
			else:
				segment_index += 1

		return packet
		
	@staticmethod
	def get_blocks_packet(colors_rgb, num_pixels):
		# the whole light string alternates statically with each color that was pressed, section by section
		# need to determine how many sections are needed across the string and determine the boundary points
		num_colors = len(colors_rgb)
		section_size = round(num_pixels / num_colors)
		packet = []
		color_index = 0
		section_index = 0
		for i in range(num_pixels):
			packet += colors_rgb[color_index]
			if section_index == section_size - 1:
				section_index = 0
				color_index = min(color_index + 1, num_colors - 1)
			else:
				section_index += 1
				
		return packet
		
	@staticmethod
	def make_rainbow_packet(num_pixels):
		colors = ["red", "orange", "yellow", "green", "blue", "purple"]
		colors_rgb = [Lights.rgb_from_color(x) for x in colors]
		packet = Lights.get_blocks_packet(colors_rgb, num_pixels)
		return packet
		
	@staticmethod
	def make_interlude_packet_plan(num_pixels):
		# rainbow blocks scrolling one direction at 50% dimming
		# a full brightness hot spot scrolling the other direction at a different speed
		# 3x around for dimming while only 1x around for rainbow
		packet = Lights.make_rainbow_packet(num_pixels)
		packet_plan = []
		
		# make the packet_plan at full brightness
		for i in range(num_pixels):
			shifted = Lights.shift_packet(packet, i, 'left')
			packet_plan.append(shifted)
			packet_plan.append(shifted)
			packet_plan.append(shifted)
		
		# make the base dimming plan
		dim_packet = [0.1] * len(packet)
		dim_packet[-15:] = [0.7, 0.7, 0.7, 0.85, 0.85, 0.85, 1.0, 1.0, 1.0, 0.85, 0.85, 0.85, 0.7, 0.7, 0.7]
		
		dim_plan = []
		for i in range(num_pixels * 3):
			dim_packet = Lights.shift_packet(dim_packet, 1, 'right')
			dim_plan.append(dim_packet)
		
		final_plan = []
		for i, packet in enumerate(packet_plan):
			dim_packet = dim_plan[i]
			final_plan.append([int(a*b) for a,b in zip(packet,dim_packet)])
					
		return final_plan
		
	@staticmethod
	def make_whole_string_packet(r, g, b, num_pixels):
		packet = []
		for i in range(num_pixels):
			packet.append(r)
			packet.append(g)
			packet.append(b)
			
		return packet
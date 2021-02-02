class Lights:
	COLOR_LIST = ["green", "red", "yellow", "blue", "orange", "white", "black"]
	
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
	def make_whole_string_packet(r, g, b, num_pixels):
		packet = []
		for i in range(num_pixels):
			packet.append(r)
			packet.append(g)
			packet.append(b)
			
		return packet
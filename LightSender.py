import sacn
from datetime import datetime
import threading

from Interlude import Interlude

BASE_MOTION_DELAY = 0.05


class LightSender:
	def __init__(self):		
		# setup the communication with the lights
		self.sender = sacn.sACNsender()
		self.sender.start()  # start the sending thread
		self.sender.activate_output(23)
		self.u23 = self.sender[23]
		self.u23.destination = "192.168.1.207"
		self.current_packet = [[[]]]
		self.t = None  # thread for handling motion
		
		# set up the light matrix mapping
		self.light_dimensions = 60, 1, 1	# L, H, D
		L, H, D = self.light_dimensions
		self.universes = [
			{
				"universe": self.u23,
				"pixel_indexes": [(0, 0, x) for x in range(L)]
			}
		]
				
		# initiate the interlude sequence across the full display
		self.controllers = {}
		self.add_controller('interlude', Interlude('interlude', self.light_dimensions, self))
		self.allocate_pixels()
		
		self.next_moving_step()
		
	def next_moving_step(self):
		now = datetime.now()
		
		# call the next_moving_step method of each controller that is active
		for controller_name, val in self.controllers.items():
			if val['is_active']:
				val['controller'].next_moving_step(now)
				
		self.t = threading.Timer(BASE_MOTION_DELAY, self.next_moving_step).start()

	def add_controller(self, controller_name, controller):
		index = len(self.controllers.keys())
		self.controllers[controller_name] = {
			"controller": controller,
			"index": index,
			"is_active": False,
			"pixel_allocation": None
		}
		
	def set_lights(self, controller_name, packet):
		pixel_ranges = self.controllers[controller_name]['pixel_allocation']
		if pixel_ranges is not None:
			# update the current packet
			range_L, range_H, range_D = pixel_ranges
			for i, grid in enumerate(packet):
				for j, row in enumerate(grid):
					start = range_L[0]
					stop = range_L[1] - 1
					self.current_packet[i][j][start:stop+1] = row

			# send the current packet to the universes
			for uni in self.universes:
				uni_packet = []
				for pixel in uni['pixel_indexes']:
					g, r, p = pixel		# grid, row, pixel
					# print(self.current_packet[g][r][p])
					uni_packet += [x for x in self.current_packet[g][r][p]]
			
			# print(uni_packet)
			uni['universe'].dmx_data = uni_packet
		
	def stop(self):
		self.sender.stop()
		
	def go_inactive(self, name):
		print(f'{name} is inactive')
		self.controllers[name]["is_active"] = False
		self.controllers[name]["controller"].update_pixel_allocation((0, 0, 0))
		
		# update the rest of the controllers pixel allocations
		self.allocate_pixels()
	
	def go_active(self, name):
		print(f'{name} is active')
		self.controllers[name]["is_active"] = True
		self.controllers['interlude']['is_active'] = False 
		
		# update the controllers pixel allocations
		self.allocate_pixels()
		
	def allocate_pixels(self):		
		num_active = len([k for k, v in self.controllers.items() if v["is_active"]])
		L, H, D = self.light_dimensions
		
		if num_active == 0:
			pixel_ranges = [([0, L-1], [0, H-1], [0, D-1])]
			self.controllers['interlude']['is_active'] = True
		else:
			new_L = L / num_active
			pixel_ranges = []
			for i in range(num_active):
				# pixel_range is tuple of L, H, D ranges
				pixel_range = [new_L*i, new_L -1], [0, H-1], [0, D-1]
				pixel_ranges.append(pixel_range)
		
		range_index = 0
		for key, value in sorted(self.controllers.items(), key=lambda x: x[1]['index']):
			if value["is_active"]:
				range_L, range_H, range_D = pixel_ranges[range_index]
				
				value["controller"].update_pixel_allocation((range_L[1] - range_L[0] + 1, range_H[1] - range_H[0] + 1, range_D[1] - range_D[0] + 1))
				value["pixel_allocation"] = range_L, range_H, range_D
				range_index += 1
			else:
				value["pixel_allocation"] = None
		
		out = [f"{k}: {v['pixel_allocation']}" for k, v in self.controllers.items()]
		print(f'Current pixel allocation is as follows: {out}')
			
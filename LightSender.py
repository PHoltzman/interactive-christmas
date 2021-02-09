import sacn
from datetime import datetime
import threading
from time import sleep

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
		self.t = None  # thread for handling motion
		
		# set up the light matrix mapping
		self.light_dimensions = L, H, D = 12, 6, 1	# L, H, D
		self.current_packet = self.make_blackout_packet()
		
		# pixel indexes are stored as left/right, up/down, forward/backward or pixel, row, grid
		
		self.universes = [
			{
				"universe": self.u23,
				"pixel_indexes": [(x, 0, 0) for x in range(12)] + 
					[(x, 1, 0) for x in range(11, -1, -1)] +
					[(x, 2, 0) for x in range(12)] + 
					[(x, 3, 0) for x in range(11, -1, -1)] +
					[(x, 4, 0) for x in range(12)] + 
					[(x, 5, 0) for x in range(11, -1, -1)]
			}
		]

		# initiate the interlude sequence across the full display
		self.controllers = {}
		self.add_controller('interlude', Interlude('interlude', self.light_dimensions, self))
		self.allocate_pixels()
		
		self.next_moving_step()
	
	def make_blackout_packet(self):
		L, H, D = self.light_dimensions
		return [[[(0, 0, 0) for i in range(L)] for j in range(H)] for k in range(D)]
		
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
			# ([0, 11], [0, 3], [0, 0])
			range_L, range_H, range_D = pixel_ranges
			for i, grid in enumerate(packet):
				for j, row in enumerate(grid):
					start = range_L[0]
					stop = range_L[1]
					try:
						self.current_packet[i][j][start:stop] = row
					except Exception:
						print(start)
						print(stop)
						print(i)
						print(j)
						raise
						
			self._send_current_packet()
						
	def _send_current_packet(self):
		# send the current packet to the universes
		for uni in self.universes:
			uni_packet = []
			for pixel in uni['pixel_indexes']:
				p, r, g = pixel
				uni_packet += [x for x in self.current_packet[g][r][p]]
			
			# print(uni_packet)
			uni['universe'].dmx_data = uni_packet
	
	def stop(self):
		print('Stopping light sender')
		for key, value in self.controllers.items():
			value['is_active'] = False
		self.allocate_pixels(is_final=True)
		self.current_packet = self.make_blackout_packet()
		self._send_current_packet()
		print('Sending final packet')
		sleep(1)
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
		
	def allocate_pixels(self, is_final=False):		
		num_active = len([k for k, v in self.controllers.items() if v["is_active"]])
		L, H, D = self.light_dimensions
		
		if num_active == 0:
			pixel_ranges = [([0, L-1], [0, H-1], [0, D-1])]
			self.controllers['interlude']['is_active'] = True if not is_final else False
		else:
			new_L = int(L / num_active)
			pixel_ranges = []
			for i in range(num_active):
				# pixel_range is tuple of L, H, D ranges
				pixel_range = [new_L*i, new_L*i+new_L-1], [0, H-1], [0, D-1]
				pixel_ranges.append(pixel_range)
		
		range_index = 0
		for key, value in sorted(self.controllers.items(), key=lambda x: x[1]['index']):
			if value["is_active"]:
				range_L, range_H, range_D = pixel_ranges[range_index]
				
				value["pixel_allocation"] = range_L, range_H, range_D
				value["controller"].update_pixel_allocation((range_L[1] - range_L[0] + 1, range_H[1] - range_H[0] + 1, range_D[1] - range_D[0] + 1))
				range_index += 1
			else:
				value["pixel_allocation"] = None
		
		out = [f"{k}: {v['pixel_allocation']}" for k, v in self.controllers.items()]
		print(f'Current pixel allocation is as follows: {out}')
			
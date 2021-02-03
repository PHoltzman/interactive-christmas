import sacn
from datetime import datetime
import threading

BASE_MOTION_DELAY = 0.05


class LightSender:
	def __init__(self, total_pixels):
		self.total_pixels = total_pixels
		self.controllers = {}
		
		# setup the communication with the lights
		self.sender = sacn.sACNsender()
		self.sender.start()  # start the sending thread
		self.sender.activate_output(23)
		self.universe = self.sender[23]
		self.universe.destination = "192.168.1.207"
		self.current_packet = []
		self.t = None  # thread for handling motion
		
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
		indexes = self.controllers[controller_name]['pixel_allocation']
		if indexes is not None:
			start = indexes[0] * 3
			stop = indexes[1] * 3 + 2
			self.current_packet[start:stop+1] = packet
			self.universe.dmx_data = self.current_packet
		
	def stop(self):
		self.sender.stop()
		
	def go_inactive(self, name):
		print(f'{name} is inactive')
		self.controllers[name]["is_active"] = False
		self.controllers[name]["controller"].update_pixel_allocation(0)
		
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
		
		if num_active == 0:
			pixel_ranges = [[0, 59]]
			self.controllers['interlude']['is_active'] = True
		elif num_active == 1:
			pixel_ranges = [[0, 59]]
		elif num_active == 2:
			pixel_ranges = [[0, 29], [30, 59]]
		elif num_active == 3:
			pixel_ranges = [[0, 19], [20, 39], [40, 59]]
		
		range_index = 0
		for key, value in sorted(self.controllers.items(), key=lambda x: x[1]['index']):
			if value["is_active"]:
				the_range = pixel_ranges[range_index]
				value["controller"].update_pixel_allocation(the_range[1] - the_range[0] + 1)
				value["pixel_allocation"] = the_range
				range_index += 1
			else:
				value["pixel_allocation"] = None
		
		out = [f"{k}: {v['pixel_allocation']}" for k, v in self.controllers.items()]
		print(f'Current pixel allocation is as follows: {out}')
			
import sacn
from datetime import datetime, time
import threading
from time import sleep

import global_vars
from Interlude import Interlude
from Lights import Lights

IS_UNIVERSE_PER_OUTPUT = False

BASE_MOTION_DELAY_SECS = 0.05
TIME_CHECK_TIMER_SECS = 5
CONTROLLER_IP = "192.168.0.105"
ACTIVITY_FILE = "/home/pi/interactive-lights/activity.txt"


class LightSender:
	def __init__(self, logger):
		self.logger = logger
		
		self.is_test_mode = False
		self.set_master_parameters()
		
		# setup the communication with the lights
		self.sender = sacn.sACNsender()
		self.sender.start()  # start the sending thread
		self.universe_senders = []
		self.universes = []

		# pixel indexes are stored as left/right, up/down, forward/backward or pixel, row, grid
		for i in range(1,11):
			self.sender.activate_output(i)
			self.universe_senders.append(self.sender[i])
				
		if IS_UNIVERSE_PER_OUTPUT:
			self.light_dimensions = L, H, D = 20, 10, 5	# L, H, D
				
			for d, sender in enumerate(self.universe_senders):
				if d < 5:
					i = d
					a = 0
				else:
					i = d - 5
					a = 10
					
				d = {
					"universe": sender,
					"pixel_indexes": [(a+0, x, i) for x in range(10)] +
						[(a+1, x, i) for x in range(9, -1, -1)] +
						[(a+2, x, i) for x in range(10)] +
						[(a+3, x, i) for x in range(9, -1, -1)] +
						[(a+4, x, i) for x in range(10)] +
						[(a+5, x, i) for x in range(9, -1, -1)] +
						[(a+6, x, i) for x in range(10)] +
						[(a+7, x, i) for x in range(9, -1, -1)] +
						[(a+8, x, i) for x in range(10)] +
						[(a+9, x, i) for x in range(9, -1, -1)]
				}
				self.universes.append(d)
		else:
			self.light_dimensions = L, H, D = 30, 10, 5	# L, H, D
				
			for d, sender in enumerate(self.universe_senders):
				i = int(d / 2)
				if d % 2 == 0:
					a = 0
					d = {
						"universe": sender,
						"pixel_indexes": [(a+0, x, i) for x in range(10)] +
							[(a+1, x, i) for x in range(9, -1, -1)] +
							[(a+2, x, i) for x in range(10)] +
							[(a+3, x, i) for x in range(9, -1, -1)] +
							[(a+4, x, i) for x in range(10)] +
							[(a+5, x, i) for x in range(9, -1, -1)] +
							[(a+6, x, i) for x in range(10)] +
							[(a+7, x, i) for x in range(9, -1, -1)] +
							[(a+8, x, i) for x in range(10)] +
							[(a+9, x, i) for x in range(9, -1, -1)] +
							[(a+10, x, i) for x in range(10)] +
							[(a+11, x, i) for x in range(9, -1, -1)] +
							[(a+12, x, i) for x in range(10)] +
							[(a+13, x, i) for x in range(9, -1, -1)] +
							[(a+14, x, i) for x in range(10)] +
							[(a+15, x, i) for x in range(9, -1, -1)] +
							[(a+16, x, i) for x in range(10)]
					}

				else:
					a = 17
					d = {
						"universe": sender,
						"pixel_indexes": [(a+0, x, i) for x in range(9, -1, -1)] +
							[(a+1, x, i) for x in range(10)] +
							[(a+2, x, i) for x in range(9, -1, -1)] +
							[(a+3, x, i) for x in range(10)] +
							[(a+4, x, i) for x in range(9, -1, -1)] +
							[(a+5, x, i) for x in range(10)] +
							[(a+6, x, i) for x in range(9, -1, -1)] +
							[(a+7, x, i) for x in range(10)] +
							[(a+8, x, i) for x in range(9, -1, -1)] +
							[(a+9, x, i) for x in range(10)] +
							[(a+10, x, i) for x in range(9, -1, -1)] +
							[(a+11, x, i) for x in range(10)] +
							[(a+12, x, i) for x in range(9, -1, -1)]
					}
				self.universes.append(d)
			
		for x in self.universe_senders:
			x.destination = CONTROLLER_IP
			
		# print(self.universes)
		
		self.t = None  # thread for handling motion
		self.time_thread = threading.Timer(TIME_CHECK_TIMER_SECS, self.time_check).start()
		self.is_active = self.time_check()
		
		# set up the light matrix mapping
		self.blackout_packet = Lights.make_blackout_packet(self.light_dimensions)
		self.current_packet = Lights.make_blackout_packet(self.light_dimensions)
		
		self.write_log_entry('SYSTEM', 'active')

		# initiate the interlude sequence across the full display
		self.controllers = {}
		self.add_controller('interlude', Interlude(self.logger, 'interlude', self.light_dimensions, self), 0)
		self.allocate_pixels()
		
		self.next_moving_step()
		
	def toggle_test_mode(self):
		self.is_test_mode = not self.is_test_mode
		self.set_master_parameters()
		self.logger.info(f'Test Mode = {self.is_test_mode}')
		
	def set_master_parameters(self):
		if self.is_test_mode:
			self.start_time = time(0,0,0)
			self.stop_time = time(23,59,59)
			self.master_dimming = 1
		else:
			self.start_time = time(16,0,0)
			self.stop_time = time(22,15,0)
			self.master_dimming = 0.5
	
	def time_check(self):
		now = datetime.now().time()
		if self.start_time <= now < self.stop_time:
			self.is_active = True
		else:
			self.is_active = False
		
		if not global_vars.STOP_THREADS:
			self.time_thread = threading.Timer(TIME_CHECK_TIMER_SECS, self.time_check).start()
	
	def next_moving_step(self):
		now = datetime.now()
		try:
		
			# call the next_moving_step method of each controller that is active
			for controller_name, val in self.controllers.items():
				if val['is_active']:
					val['controller'].next_moving_step(now)
				
			if not global_vars.STOP_THREADS:
				self.t = threading.Timer(BASE_MOTION_DELAY_SECS, self.next_moving_step).start()
		except Exception:
			self.logger.error('Encountered exception in next moving step thread. Capturing details and hoping things continue to work and/or fix themselves', exc_info=True)

	def add_controller(self, controller_name, controller, ordering_index):
		self.controllers[controller_name] = {
			"controller": controller,
			"index": ordering_index,
			"is_active": False,
			"pixel_allocation": None
		}
		
	def set_lights(self, controller_name, packet):
		try:
			pixel_ranges = self.controllers[controller_name]['pixel_allocation']
			if pixel_ranges is not None:
				# update the current packet
				range_L, range_H, range_D = pixel_ranges
				for i, grid in enumerate(packet):
					if not (range_D[0] <= i <= range_D[1]):
						continue
					for j, row in enumerate(grid):
						if not (range_H[0] <= j <= range_H[1]):
							continue
						self.current_packet[i][j][range_L[0]:range_L[1]+1] = row
							
				self._send_current_packet()
		except Exception:
			self.logger.error(
				f'Encountered error setting lights for controller[{controller_name}]. Assuming it is a transient problem that will resolve itself next time',
				exc_info=True
			)
						
	def _send_current_packet(self):
		if self.is_active:
			packet = self.current_packet
		else:
			packet = self.blackout_packet
			
		# send the current packet to the universes
		try:
			for uni in self.universes:
				uni_packet = []
				for pixel in uni['pixel_indexes']:
					p, r, g = pixel
					uni_packet += [int(self.master_dimming * x) for x in packet[g][r][p]]
				
				# print(uni_packet)
				uni['universe'].dmx_data = uni_packet
		except Exception:
			self.logger.error('Encountered error sending the current packet. Assuming it is a transient problem that will resolve itself next time', exc_info=True)
	
	def stop(self):
		self.logger.info('Stopping light sender')
		for key, value in self.controllers.items():
			value['is_active'] = False
			if key != "interlude":
				value['controller'].controller.close()
		
		self.write_log_entry('SYSTEM', 'inactive')
		self.allocate_pixels(is_final=True)
		self.current_packet = self.blackout_packet
		self._send_current_packet()
		self.logger.info('Sending final packet')
		
		self.logger.info('Setting variable to stop threads')		
		global_vars.STOP_THREADS = True
		sleep(1)
		
		self.logger.info('Stopping sender')
		self.sender.stop()
		self.logger.info('Shutdown complete!')
		
	def go_inactive(self, name):
		self.logger.info(f'{name} is inactive')
		self.controllers[name]["is_active"] = False
		self.write_log_entry(name, 'inactive')
		
		# update the rest of the controllers pixel allocations
		self.allocate_pixels()
	
	def go_active(self, name):
		self.logger.info(f'{name} is active')
		self.controllers[name]["is_active"] = True
		self.controllers['interlude']['is_active'] = False
		self.write_log_entry(name, 'active')
		
		# update the controllers pixel allocations
		self.allocate_pixels()
		
	def write_log_entry(self, controller_name, state):
		try:
			now = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
			entry = f"{now} {controller_name} {state}\n"
			with open(ACTIVITY_FILE, 'a') as f:
				f.write(entry)
		except Exception:
			self.logger.error('Encountered error writing to activity log file', exc_info=True)
			
	@staticmethod
	def determine_L_vals(L, num_active):
		# first determine the allocation size for each
		new_L = int(L / num_active)
		L_array = [new_L] * num_active
		add_ind = 0
		while sum(L_array) < L:
			L_array[add_ind] += 1
			add_ind += 1
			
		# now generate the actual cutoff points for each
		L_ranges = []
		for i, val in enumerate(L_array):
			L_ranges.append((sum(L_array[:i]), sum(L_array[:i+1])-1))
			
		return L_ranges
		
	def allocate_pixels(self, is_final=False):
		try:
			num_active = len([k for k, v in self.controllers.items() if v["is_active"]])
			L, H, D = self.light_dimensions
			
			if num_active == 0:
				pixel_ranges = [([0, L-1], [0, H-1], [0, D-1])]
				self.controllers['interlude']['is_active'] = True if not is_final else False
			else:
				L_ranges = self.determine_L_vals(L, num_active)
					
				pixel_ranges = []
				for item in L_ranges:
					# pixel_range is tuple of L, H, D ranges
					pixel_range = [item[0], item[1]], [0, H-1], [0, D-1]
					pixel_ranges.append(pixel_range)
			
			range_index = 0
			for key, value in sorted(self.controllers.items(), key=lambda x: x[1]['index']):
				shared_left = shared_right = False
				if value["is_active"]:
					if range_index > 0:
						shared_left = True
					if len(pixel_ranges) > 1 and range_index < len(pixel_ranges) - 1:
						shared_right = True
					range_L, range_H, range_D = pixel_ranges[range_index]
					
					value["pixel_allocation"] = range_L, range_H, range_D
					value["controller"].update_pixel_allocation(
						light_dimensions = (range_L[1] - range_L[0] + 1, range_H[1] - range_H[0] + 1, range_D[1] - range_D[0] + 1),
						is_left_shared=shared_left,
						is_right_shared=shared_right
					)
					range_index += 1
				else:
					value["pixel_allocation"] = None
			
			out = [f"{k}: {v['pixel_allocation']}" for k, v in self.controllers.items()]
			self.logger.info(f'Current pixel allocation is as follows: {out}')
		except Exception:
			self.logger.error('Encountered error allocating pixels. Assuming it will take care of itself with next button push.', exc_info=True)
			
import sched
import threading
from datetime import datetime, timedelta

import global_vars
from BaseController import BaseController, PacketPlan
from Lights import Lights

class Drums(BaseController):
	def __init__(self, controller, logger, name, light_dimensions, light_sender, gui):
		super().__init__(controller, logger, name, light_dimensions, light_sender, gui)
		
		self.time_delay = 0.05
		
		self.mode = 0  # 0 = pulse wipe spread from corners, 1 = boxes, 2 = vertical, 3 = horizontal, 4 = depthal

		# for modes != 0
		self.color_masks = {
			"red": [[[]]],
			"yellow": [[[]]],
			"blue": [[[]]],
			"green": [[[]]],
			"orange": [[[]]]
		}
		
		# for mode 1
		self.color_spread_map = {}
		
		self.current_packet_plans = []
			
	def update_pixel_allocation(self, light_dimensions, **kwargs):
		self.light_dimensions = L, H, D = light_dimensions
		self.create_allocation_and_masks(mode=self.mode)
		self.create_spread_starting_point()
	
	def create_spread_starting_point(self):
		L, H, D = self.light_dimensions
		
		self.color_spread_map = {
			"red": {
				"starts": [(0, 0, 0), (L-1, H-1, D-1)],
				"pulse": 3
			},
			"yellow": {
				"starts": [(0, H-1, 0), (L-1, 0, D-1)],
				"pulse": 3
			},
			"blue": {
				"starts": [(L-1, H-1, 0), (0, 0, D-1)],
				"pulse": 3
			},
			"green": {
				"starts": [(L-1, 0, 0), (0, H-1, D-1)],
				"pulse": 3
			},
			"orange": {
				"starts": [(int(L/2), int(H/2), int(D/2))],
				"pulse": 2
			}
		}

	def create_allocation_and_masks(self, mode=1):
		L, H, D = self.light_dimensions
		
		# establish the location for each drum on the grid
		if mode == 0:  # meteors
			return
			
		elif mode == 1:  # box
			L_split = int(L/2)
			H_split = int(H/2)
			red = (0, L_split), (0, H_split), (0, D)
			yellow = (0, L_split), (H_split, H), (0, D)
			green = (L_split, L), (0, H_split), (0, D)
			blue = (L_split, L), (H_split, H), (0, D)	
			orange = (int(L/4), int(L*3/4)), (int(H/4)+1, int(H*3/4)), (0, D)
			
		elif mode == 2:  # vertical
			L_split = int(L/5)
			red = (0*L_split, 1*L_split), (0, H), (0, D)
			yellow = (1*L_split, 2*L_split), (0, H), (0, D)
			orange = (2*L_split, 3*L_split), (0, H), (0, D)
			blue = (3*L_split, 4*L_split), (0, H), (0, D)
			green = (4*L_split, 5*L_split), (0, H), (0, D)
			
		elif mode == 3:  # horizontal
			H_split = int(H/5)
			red = (0, L), (0*H_split, 1*H_split), (0, D)
			yellow = (0, L), (1*H_split, 2*H_split), (0, D)
			orange = (0, L), (2*H_split, 3*H_split), (0, D)
			blue = (0, L), (3*H_split, 4*H_split), (0, D)
			green = (0, L), (4*H_split, 5*H_split), (0, D)
			
		elif mode == 4:  # depthal
			D_split = int(D/5)
			red = (0, L), (0, H), (0*D_split, 1*D_split)
			yellow = (0, L), (0, H), (1*D_split, 2*D_split)
			orange = (0, L), (0, H), (2*D_split, 3*D_split)
			blue = (0, L), (0, H), (3*D_split, 4*D_split)
			green = (0, L), (0, H), (4*D_split, 5*D_split)
			
		self.color_masks = {
			"red": self.make_light_mask(self.light_dimensions, red),
			"yellow": self.make_light_mask(self.light_dimensions, yellow),
			"blue": self.make_light_mask(self.light_dimensions, blue),
			"green": self.make_light_mask(self.light_dimensions, green),
			"orange": self.make_light_mask(self.light_dimensions, orange)
		}
			
	@staticmethod
	def make_light_mask(light_dimensions, mask_ranges):
		L, H, D = light_dimensions
		l, h, d = mask_ranges
		mask = []
		for i in range(D):
			grid = []
			for j in range(H):
				row = [0.0 for x in range(L)]
				if j >= h[0] and j < h[1] and i >= d[0] and i < d[1]:
					row[l[0]:l[1]] = [1.0 for x in range(l[1]-l[0])]
				grid.append(row)
			mask.append(grid)
			
		return mask					
			
	def check_for_inactivity(self):
		if self.is_active:
			if (datetime.now() - self.last_input_datetime).total_seconds() > 15:
				# this controller is now inactive so do stuff accordingly
				self.is_active = False
				self.mode = 0
								
				# tell the rest of the system that they can release our pixels
				self.light_sender.go_inactive(self.name)
		
		if not global_vars.STOP_THREADS:
			t = threading.Timer(5, self.check_for_inactivity).start()
	
	def on_button_pressed(self, button):
		super().on_button_pressed(button)
		
		# when a drum is hit, light up in that color
		color = self.get_friendly_button_name(button)
		self.logger.info(f"{color} press")
		if color in ['red', 'yellow', 'blue', 'green', 'orange']:
			L, H, D = self.light_dimensions
		
			if self.mode == 0:
				try:
					for starting_point in self.color_spread_map[color]["starts"]:
						packet_time_series = Lights.make_meteor_packet_time_series(
							color_rgb=Lights.rgb_from_color(color), 
							light_dimensions=self.light_dimensions,
							start_pixel=starting_point, 
							pulse_size=self.color_spread_map[color]["pulse"],
							frames=8
						)
						self.current_packet_plans.append(PacketPlan(packet_time_series, time_delay=self.time_delay))
				except KeyError:
					self.logger.error('Error finding color starting point for mode 0. Skipping for now and will try again next time')
				
			else:
				# Make the pulse plan and multiply by the appropriate dimming mask
				packet_time_series = Lights.make_pulse_packet_time_series(
					light_dimensions=self.light_dimensions,
					color_rgb=Lights.rgb_from_color(color),
					frames=4
				)
				packet_time_series = Lights.apply_dim_time_series(packet_time_series, [self.color_masks[color]]*len(packet_time_series))
			
				self.current_packet_plans.append(PacketPlan(packet_time_series, time_delay=self.time_delay))
				
		elif color == 'plus':
			self.mode = 0 if self.mode == 4 else self.mode + 1
			self.light_sender.write_log_entry(self.name, f"mode_{self.mode}_active")
			self.create_allocation_and_masks(mode=self.mode)
			
		elif color == 'minus':
			self.mode = 4 if self.mode == 0 else self.mode - 1
			self.light_sender.write_log_entry(self.name, f"mode_{self.mode}_active")
			self.create_allocation_and_masks(mode=self.mode)
	
	def update_lights(self):
		# grab the current index for all active plans and merge those plans together
		# if there are no active plans left, then set to black
		if self.current_packet_plans:
			packets_to_merge = [x.get_current_packet() for x in self.current_packet_plans]
			try:
				packet = Lights.merge_packets(packets_to_merge, self.light_dimensions)
			except IndexError:
				self.logger.warning('Index error when merging packets, likely due to light dimensions being reallocated. Setting to black for now and expecting it to fix itself next time around')
				packet = Lights.make_whole_string_packet((0, 0, 0), self.light_dimensions)
		else:
			packet = Lights.make_whole_string_packet((0, 0, 0), self.light_dimensions)
			
		# invoke light updater
		self.light_sender.set_lights(self.name, packet)
		
	def next_moving_step(self, current_time):
		is_any_advanced = False
		indexes_to_remove = []
		for i, packet_plan in enumerate(self.current_packet_plans):
			is_advanced, is_ended = packet_plan.advance_packet_plan(current_time)
			if is_advanced:
				is_any_advanced = True
			if is_ended:
				indexes_to_remove.append(i)
				
		indexes_to_remove.sort(reverse=True)
		for ind in indexes_to_remove:
			try:
				self.current_packet_plans.pop(ind)
			except IndexError:
				pass

		if is_any_advanced:
			# invoke light updater
			self.update_lights()
		
	@staticmethod
	def get_friendly_button_name(button):
		button_mapping = {
			"button_a": "blue",
			"button_b": "green",	
			"button_x": "red",
			"button_y": "yellow",
			"button_trigger_l": "orange",
			"button_select": "select",
			"button_start": "start",
			"button_mode": "minus",
			"button_thumb_l": "plus"
		}
		try:
			return button_mapping[button.name]
		except KeyError:
			return button.name
			
	@staticmethod
	def get_friendly_axis_name(axis_name):
		axis_mapping = {
			"hat": "dpad",
			"axis_r": "whammy",
			"trigger_l": "selector"
		}
		try:
			return axis_mapping[axis_name]
		except KeyError:
			return 'unknown'
	
	@staticmethod
	def get_axis_details(axis):
		hat_mapping = {
			(0, 1): "up",
			(1, 1): "right_up",
			(1, 0): "right",
			(1, -1): "right_down",
			(0, -1): "down",
			(-1, -1): "left_down",
			(-1, 0): "left",
			(-1, 1): "left_up"
		}
		friendly_name = Drums.get_friendly_axis_name(axis.name)
		if friendly_name == 'dpad':
			value = hat_mapping[(axis.x, axis.y)]
		elif friendly_name == 'whammy':
			value = axis.x
		elif friendly_name == 'selector':
			value = Drums.get_selector_value(axis.value)
		else:
			value = 'unknown'
			
		return friendly_name, value

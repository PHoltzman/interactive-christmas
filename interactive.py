import signal
import logging
import logging.handlers
import threading
import os
import sys
from datetime import datetime

from xbox360controller import Xbox360Controller

import global_vars
from Guitar import Guitar
from Drums import Drums
from Car import Car
from LightSender import LightSender
from Gui import Gui

os.environ['DISPLAY'] = ':0.0'
gui = None

# setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_formatter = logging.Formatter(fmt="%(asctime)s.%(msecs)03d %(levelname)s %(filename)s[%(funcName)s] %(message)s", datefmt='%Y-%m-%dT%H:%M:%S')
sh = logging.StreamHandler(stream=sys.stdout)
sh.setFormatter(log_formatter)
logger.addHandler(sh)
trfh = logging.handlers.TimedRotatingFileHandler("logs/log.log", when="midnight")
trfh.setFormatter(log_formatter)
logger.addHandler(trfh)

def sigterm_handler(signal, frame):
	logger.info('Received SIGTERM')
	light_sender.stop()
	if gui is not None:
		gui.window.close()
	sys.exit(0)

signal.signal(signal.SIGTERM, sigterm_handler)


def establish_controller(index, logger, light_sender, gui):
	try:
		controller = Xbox360Controller(index=index)
		logger.info(controller.name)
	except Exception:
		logger.error(f'Encountered exception initiating controller at index {index}', exc_info=True)
		return
		
	if 'Drum' in controller.name:
		light_sender.add_controller('drums', Drums(controller, logger, 'drums', (0, 0, 0), light_sender, gui), 1)
	elif 'WingMan' in controller.name:
		controller.axis_threshold=0.05
		light_sender.add_controller('car', Car(controller, logger, 'car', (0, 0, 0), light_sender, gui), 2)
	elif 'Guitar' in controller.name:
		light_sender.add_controller('guitar1', Guitar(controller, logger, 'guitar1', (0, 0, 0), light_sender, gui), 3)
	else:
		logger.error(f'Unrecognized controller found with name {controller.name}. Skipping it.')
		controller.close()
		

def check_controllers():
	indexes = [0, 1, 2]
	for index in indexes:
		establish_controller(index, logger, light_sender, gui)
	
	
try:
	light_sender = LightSender(logger)
	# gui = Gui()
	
	check_controllers()	
	
	if gui is not None:
		gui.set_guitar_status('Inactive')
		gui.set_car_status('Inactive')
		gui.set_drum_status('Inactive')
		
	signal.pause()
		
except KeyboardInterrupt:
	logger.info('Received keyboard interrupt')
	light_sender.stop()
	if gui is not None:
		gui.window.close()
	sys.exit(1)
	
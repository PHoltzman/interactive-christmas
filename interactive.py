import signal
import logging
import logging.handlers
import os
import sys
from datetime import datetime

from xbox360controller import Xbox360Controller

from Guitar import Guitar
from Drums import Drums
from Car import Car
from LightSender import LightSender
from Gui import Gui


try:
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
	
	light_sender = LightSender(logger)
	os.environ['DISPLAY'] = ':0.0'
	# gui = Gui()
	gui = None
	
	with Xbox360Controller(0, axis_threshold=0.2) as controller:
		controller.info()
		light_sender.add_controller('drums', Drums(controller, logger, 'drums', (0, 0, 0), light_sender, gui))
		
		with Xbox360Controller(2, axis_threshold=0.05) as controller:
			controller.info()
			light_sender.add_controller('car', Car(controller, logger, 'car', (0, 0, 0), light_sender, gui))
				
			with Xbox360Controller(1, axis_threshold=0.2) as controller:
				controller.info()
				light_sender.add_controller('guitar1', Guitar(controller, logger, 'guitar1', (0, 0, 0), light_sender, gui))
				
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
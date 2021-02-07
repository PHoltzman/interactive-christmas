import signal
import sys
from datetime import datetime

from xbox360controller import Xbox360Controller

from Guitar import Guitar
from Car import Car
from LightSender import LightSender


try:
	light_sender = LightSender()
	
	# with Xbox360Controller(0, axis_threshold=0.2) as controller:
		# controller.info()
		# light_sender.add_controller('guitar1', Guitar(controller, 'guitar1', 0, light_sender))
		
		# with Xbox360Controller(1, axis_threshold=0.05) as controller:
			# controller.info()
			# light_sender.add_controller('car', Car(controller, 'car', 0, light_sender))
			
	signal.pause()
		
except KeyboardInterrupt:
	light_sender.stop()
	sys.exit(1)
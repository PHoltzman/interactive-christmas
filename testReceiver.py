import sacn
import pygame
import sys
import time
import os

# os.environ["SDL_VIDEODRIVER"] = "dummy"


BLACK = (0, 0, 0)
DIM = (50, 50, 50)

WINDOW_HEIGHT = 700
WINDOW_WIDTH = 1200
SCREEN_OFFSET_X = 50
SCREEN_OFFSET_Y = 50

PIXEL_SIZE = 2

X_SPACE = 50
Y_SPACE = 50
Z_SPACE = 5

universe_count = 10

universe_mapping = {}
for uni in range(universe_count):
	uni += 1
	universe_mapping[uni] = {}
	pixels = []
	locations = []
	if uni <= 5:
		z = uni - 1
	elif uni <= 10:
		z = uni - 6
	else:
		z = uni - 11
	
	if (uni-1) % 5 == 0:
		Z_OFF = 0
	else:
		Z_OFF += Z_SPACE
		
	for i in range(0, 10):
		if uni <= 5:
			X_OFF = 0
			x = i
		elif uni <= 10:
			X_OFF = X_SPACE * 9
			x = 10 + i
		else:
			X_OFF = X_SPACE * 18
			x = 20 + i
			
		for j in range(0, 10):
			if i % 2 == 0:
				y = j
			else:
				y = 9 - j
			
			pixels += [(x, y, z)]
			X = i*X_SPACE+X_OFF+Z_OFF + SCREEN_OFFSET_X
			Y = y*Y_SPACE+Z_OFF
			Y = WINDOW_HEIGHT - Y - SCREEN_OFFSET_Y
			locations += [(X, Y)]
			
	universe_mapping[uni]["pixels"] = pixels
	universe_mapping[uni]["locations"] = locations


def callback(packet):
	uni = packet.universe
	data = packet.dmxData
	# print(uni)
	i = 0
	for loc in universe_mapping[uni]["locations"]:
		rect = pygame.Rect(loc[0], loc[1], PIXEL_SIZE, PIXEL_SIZE)
		color = (data[i], data[i+1], data[i+2])
		if color == (0, 0, 0):
			color = DIM
		# print(loc, color)
		pygame.draw.rect(SCREEN, color, rect, 0)
		i += 3
	
	pygame.display.update()

try:
	receiver = sacn.sACNreceiver()
	receiver.start()
	for uni in universe_mapping.keys():
		receiver.register_listener('universe', callback, universe=uni)
	pygame.init()
	pygame.display.list_modes()
	SCREEN = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
	SCREEN.fill(BLACK)
	
	# initialize the grid
	for uni, val in universe_mapping.items():
		for loc in val["locations"]:
			rect = pygame.Rect(loc[0], loc[1], PIXEL_SIZE, PIXEL_SIZE)
			pygame.draw.rect(SCREEN, DIM, rect, 0)
	
	pygame.display.update()
	
	# time.sleep(10)
	
	while True:  # the while loop that will keep your display up and running!
		for event in pygame.event.get():  # the for event loop, keeping track of events,
			if event.type == pygame.QUIT:  # and in this case, it will be keeping track of pygame.QUIT, which is the X or the top right
				 pygame.quit()  # stops pygame
		
except Exception as e:
	print('Exception hit')
	print(e)
	
finally:
	print('Quitting pygame...')
	pygame.quit()
	print('Stopping sACN Receiver...')
	receiver.stop()
	print('Exiting')
	sys.exit()
	print('Complete!')
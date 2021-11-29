import PySimpleGUI as sg

class Gui:
	def __init__(self):
		guitar_column = [
			[sg.Text(size=(40, 1), key="-GUITAR_STATUS-")],
			[sg.Text(size=(40, 1), key="-GUITAR_MODE-")],
			[sg.Text('_'*40) ],
			[sg.Text("Guitar instructions go here")]
		]
		
		car_column = [
			[sg.Text(size=(40, 1), key="-CAR_STATUS-")],
			[sg.Text(size=(40, 1), key="-CAR_MODE-")],
			[sg.Text('_'*40) ],
			[sg.Text("Car instructions go here")]
		]
		
		drum_column = [
			[sg.Text(size=(40, 1), key="-DRUM_STATUS-")],
			[sg.Text(size=(40, 1), key="-DRUM_MODE-")],
			[sg.Text('_'*40) ],
			[sg.Text("Drum instructions go here")]
		]

		# ----- Full layout -----
		layout = [
			[
				sg.Column(guitar_column),
				sg.VSeperator(),
				sg.Column(car_column),
				sg.VSeperator(),
				sg.Column(drum_column)
			]
		]

		self.window = sg.Window("Broomfield Lights | Interactive Display", layout).Finalize()
		self.window.Maximize()
		
	def set_status(self, status, name):
		if name == 'guitar':
			self.set_guitar_status(status)
		elif name == 'car':
			self.set_car_status(status)
		elif name == 'drum':
			self.set_drum_status(status)
		
	def set_guitar_status(self, status):
		self.window["-GUITAR_STATUS-"].update(status)
		
	def set_guitar_mode(self, mode):
		self.window["-GUITAR_MODE-"].update(mode)
		
	def set_car_status(self, status):
		self.window["-CAR_STATUS-"].update(status)
		
	def set_car_mode(self, mode):
		self.window["-CAR_MODE-"].update(mode)
		
	def set_drum_status(self, status):
		self.window["-DRUM_STATUS-"].update(status)
		
	def set_drum_mode(self, mode):
		self.window["-DRUM_MODE-"].update(mode)

	
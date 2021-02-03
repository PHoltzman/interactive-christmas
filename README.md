# interactive-christmas
Python code to accept input from controllers and use it to run Christmas lights. As of 2/1/2021, this is a work in progress and will likely continue for the rest of the year and beyond. The ultimate goal is to have multiple different input devices controlling a 3 dimensional grid of LED RGB pixels. The current code accepts in put from a Guitar Hero guitar and a Logitech WingMan Formula GP steering wheel / gas / brake controller and uses it to drive a single string of about 60 pixels. The controllers are each given a subsection of the lights to control and the code automatically detects when a controller is no longer being used and reallocates the space to the remaining controllers still in use.

I am currently running on a raspberry pi 2 and using a SanDevices E682 to convert the E1.31 data into actual commands to the pixels.

Check out broomfieldlights.com for way more about my Christmas light show and related things. The intent is to setup a secondary display in my side yard where people who come to see our light show can have a more hands-on experience and actually interact with some Christmas lights as well.

## TODO list
- Get more controllers and interface with them (guitar hero drum kit? DJ Hero scratch pad?)
- Add ability for controller to auto reconnect if it gets disconnected (guitar cord is a bit flaky when pulled)
- Add sound when the guitar is played
	- Have a mode for chords? Another mode for solo effects?
		- Perhaps use the headstock buttons for chords and the neck buttons for soloing?
	- Allow chords to be in different keys or just have 1 set of options? (I, IV, V, VIm, IIm)
- Move from 1 dimensional lights to 2D or 3D (my brain hurts trying to figure out how to make this interesting creatively and fabricate all the patterns...1D has been hard enough)
- Fix any lingering issues with the reallocation of lights not going smoothly
- Do something with the brake pedal and 2 other steering wheel buttons on the Logitech controller
- Figure out a merge effect where all controllers work together to affect all of the lights rather than subdividing the pixels
	- To start, have a button on each controller than can be used to enter this mode
		- "Start" on guitar, bottom left button on steering wheel
		- Only enter the mode if all active controllers are pressing their magic button simultaneously
	- Perhaps have a different "Golden button" on a pedestal that someone can hit to enter the mode
- Waterproof the controllers
- Build a stand for the Logitech controller
- Test out routerless operation with crossover cable directly connection rpi and E682

## TO-DONE list
- Create an interlude sequence to play when all controllers have gone inactive in order to draw attention

# interactive-christmas
Python code to accept input from controllers and use it to run Christmas lights. As of 3/1/2021, this is a work in progress and will likely continue for the rest of the year and beyond. The ultimate goal is to have multiple different input devices controlling a 3 dimensional grid of LED RGB pixels. For this first year, I am anticipating a grid that is 20 pixels long by 10 pixels high, by 10 pixels deep, though that is just a guess at what is reasonably achievable and won't cost too much. The controllers are each given a subsection of the lights to control and the code automatically detects when a controller is no longer being used and reallocates the space to the remaining controllers still in use.

I am currently running on a raspberry pi 2 and using a SanDevices E682 to convert the E1.31 data into actual commands to the pixels.

Check out broomfieldlights.com for way more about my Christmas light show and related things. The intent is to setup a secondary display in my side yard (or possibly neighbor's yard) where people who come to see our light show can have a more hands-on experience and actually interact with some Christmas lights as well.

## TODO list
- Add ability for controller to auto reconnect if it gets disconnected (guitar cord is a bit flaky when pulled)
- Figure out why guitar dimming seems to encroach on neighbor and why allocation seems to have issues when 2 are active together. Might be related to allocation issues. Not sure but something is going on
- Figure out a merge effect where all controllers work together to affect all of the lights rather than subdividing the pixels
	- To start, have a button on each controller than can be used to enter this mode
		- "Start" on guitar, bottom left button on steering wheel
		- Only enter the mode if all active controllers are pressing their magic button simultaneously
	- Perhaps have a different "Golden button" on a pedestal that someone can hit to enter the mode
- Add more games
	- Play 2 person game of tag or something like that (similar to catch the pixel but someone else controls the target with a different controller)
- Add third dimension of lights
- Get additional controllers (DJ Hero scratch pad?)
- Build an adjustable stand for the Logitech controller
- Add sound when the guitar is played
	- Have a mode for chords? Another mode for solo effects?
		- Perhaps use the headstock buttons for chords and the neck buttons for soloing?
	- Allow chords to be in different keys or just have 1 set of options? (I, IV, V, VIm, IIm)
- Waterproof the controllers
- Test out routerless operation with crossover cable directly connecting rpi and E682
- Figure out how to present instructions in an easily consumable way for people who walk up

## TO-DONE list
- Create an interlude sequence to play when all controllers have gone inactive in order to draw attention
- Have lights mapped across multiple universes and work out how to send properly
- Move from 1 dimensional lights to 2D or 3D (my brain hurts trying to figure out how to make this interesting creatively and fabricate all the patterns...1D has been hard enough)
- Make guitar motion effects able to scroll in any direction (right, left, up, down, angles; use left/right on d-pad to toggle the direction)
- Have light sender deactivate all controllers at shutdown and black out the lights
- initial allocation to guitar doesn't go to black as expected
- Get Car working with new setup of light_dimensions
- interface with guitar hero drum kit
- Figure out how to do one time effects (pulse and fade out when a drum is hit but not repeating...put each drum in a corner and have the kick be the center square and have them pulse when hit)
- Refactor car gas pedal to control vertical shifting and figure out time delays
- Add mode to drums to have each color pulse out from its corner
- Create catch the pixel game with car controller with a chase pixel, target pixel, and walls.

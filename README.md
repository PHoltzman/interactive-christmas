# interactive-christmas
Python code to accept input from controllers and use it to run Christmas lights. As of 12/7/2021, this is a work in progress (but is functional) and will likely continue for the rest of the year and beyond. The ultimate goal is to have multiple different input devices controlling a 3 dimensional grid of LED RGB pixels. For this first year, we have a matrix of 1000 pixels that is 20 long x 10 high x 10 deep. The controllers are each given a subsection of the lights to control and the code automatically detects when a controller is no longer being used and reallocates the space to the remaining controllers still in use.

I am currently running on a raspberry pi 2 and using a SanDevices E682 to convert the E1.31 data into actual commands to the pixels.

Check out broomfieldlights.com for way more about my Christmas light show and related things. This runs as a secondary display in my neighbor's yard where people who come to see our light show can have a more hands-on experience and actually interact with some Christmas lights as well. For more details on this display specifically, go to https://broomfieldlights.com/interactive-light-display/



## TODO list
- Add virtual light display option for testing
- Build MazeGame
- Add 500 more pixels to the display to make 30x10x5
- Build DDR controller
- Add delayed game start with quick countdown
- Put game title up when switching to a game
- Put score after losing a game
- Build PongGame
- Build CentipedeGame
- Build PixelCatchGame
- Build DrumHeroGame
- Build GuitarHeroGame
- Reduce lag on drum (perhaps pre-calculate the lights better)
- Update readme to document better the general structure and how the various threads interact
- Waterproof the controllers
- Create a user interface to display what's happening and basic instructions
- Add ability for controller to auto reconnect if it gets disconnected (guitar cord is a bit flaky when pulled)
- Figure out a merge effect where all controllers work together to affect all of the lights rather than subdividing the pixels?
	- To start, have a button on each controller than can be used to enter this mode
		- "Start" on guitar, bottom left button on steering wheel
		- Only enter the mode if all active controllers are pressing their magic button simultaneously
	- Perhaps have a different "Golden button" on a pedestal that someone can hit to enter the mode
- Add more games
	- Play 2 person game of tag or something like that (similar to catch the pixel but someone else controls the target with a different controller)?
	- catch falling objects game (control size of catcher, mode to move along bottom or along front face, variable speed of objects)
	- guitar hero or drum hero games where you play the right colors at the right time 
	- Drive through a maze without touching the walls (mode to control width of track and/or complexity)
	- Snake (select between 2D on the front grid and 3D, use car controller to move)
	- Centipede?
- Get additional controllers (DJ Hero scratch pad?)
- Add other ways to interact (website form? text? tweet? camera?)
- Add sound when the guitar is played
	- Have a mode for chords? Another mode for solo effects?
		- Perhaps use the headstock buttons for chords and the neck buttons for soloing?
	- Allow chords to be in different keys or just have 1 set of options? (I, IV, V, VIm, IIm)
- Build foot piano
 
## TO-DONE list
- Maintain snake length across reallocation in SnakeGame
- Build SnakeGame
- Figure out why enemies disappear in car game sometimes after board resets
- Build other 5 panels
- Figure out why guitar dimming (and other things) seems to encroach on neighbor and why allocation seems to have issues when 2 are active together. Might be related to allocation issues. Not sure but something is going on (off by one error when pixels allocated to controllers were merged back into the master packet, which caused the master packet to increase in size over time)
- Add option for enemies in car game (variable number based on button)
- Make game wall density selectable
- Use brake for car to go down rather than a reverse button
- Make guitar motions and wipes go all directions
- Create instruction sheets to present instructions in an easily consumable way for people who walk up
- Add tracking for how long each controller is in use
- Auto turn on/off display based on time of day
- Use paddle shifters for car to go in third dimension
- Add third dimension of lights
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

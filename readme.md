Problem statements:
===================

#### CHALLENGE 1 : simple circle

Given a window of 50x50 size, draw an empty circle of radius *r* at coordinate (x,y) with a character *char* as base drawing material. Those arguments should be passed to the program via the command line. The character should be printed white on a black background.

#### CHALLENGE 2 : interactive ASCII map

Generate or draw an ascii map, either using [rexpaint](https://www.gridsagegames.com/rexpaint/), or by generating an ascii map based on an image. The map should have distinctive colours for each country/region. Then use the mouse coordinates to check the background colour of the cell against a dictionary which have the RGB value of the background as a key and the country's name as a value. Then blit that console to the root, slightly offset from the mouse point.

#### CHALLENGE 3 : console fading

Fade from one offscreen console to another  using the console's *bg_alpha* and *fg_alpha* values.

#### CHALLENGE 4 : ASCII map zoom and drag

Using the map used in problem 2, implement :
 * a zoom functionnality to zoom in/out on a specific area of the map with the mouse wheel.
 * a drag and drop functionnality to move around the map.

#### CHALLENGE 5 : ASCII map combined

Combine challenge 2 and 4 in only one, making it as clean as possible.

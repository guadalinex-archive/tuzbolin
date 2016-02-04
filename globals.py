#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Authors:
#   Félix del Rio Benigno <fario@emergya.es>
#   Metin Akdere <makdere@emergya.es>
#
# Copyright 2008 Emergya, sca. (www.emergya.es)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of version 2 of the GNU General Public
# License as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
'''Global and constant variables which are always same for each game.
Also sets the game environment holding variables that will be accessed from
other modules, avoiding ciclical import.
Also including basic configuration variables for each game loaded from the
config file.'''

from pygame.locals import *
import yaml

DISPLAY_SIZE = (1024, 768) # game resolution
DISPLAY_FLAGS = HWACCEL | DOUBLEBUF# | FULLSCREEN ## screen flags
FPS = 26.0 # desired frames per second
FIELD_SIZE = (900, 550) # game field size
FIELD_TOP_LEFT = ((DISPLAY_SIZE[0] - FIELD_SIZE[0]) / 2.0,
                  (DISPLAY_SIZE[1] - FIELD_SIZE[1]) / 2.0)
FIELD_CONCAVE_FACTOR = 0.55 # factor to apply a force towards the center of the field
FIELD_FRICTION = 0.018 # friction to apply to the balls
GOAL_SIZE = 20, 100

USE_KEYCONTROLLER = 0

 
## configuration for each game from default_conf.yml. 
## Those can be alignment of the bars, number of the penguins of each bar, bars
## that are controlled by the wiimote, game duration, etc..
config = yaml.load(open('./default_conf.yml'))

## shorcuts for several config options
sound = config['sound']
debug = config['debug']
fps = config['fps']

## Game states
ST_WAITING = 0
ST_PLAYING = 1
ST_END = 2

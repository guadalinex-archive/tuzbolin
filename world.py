#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Authors:
#   Félix del Rio Benigno <fario@emergya.es>
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
'''This module will contain shorcuts and helpers to manage the interaction between the actors and the ODE world. 
   Moreover, includes mainly conversion functions between world coordinates and pixel coordinates because pyode and pygame uses
   different coordinating system '''

import ode
import globals

_half_screen_w = globals.DISPLAY_SIZE[0] / 2.0
_half_screen_h = globals.DISPLAY_SIZE[1] / 2.0

def init_ode():
    '''Inits ode global variables needed to start the simulation'''
    globals.ode_world = ode.World() # world is the object that does the dynamic symulation
    #globals.ode_world.setGravity((0,0,-9.81))
    
    globals.ode_space = ode.HashSpace() # space is does the collision test and response
    
def w_to_pix(p):
    '''Convert world coordinates to pixel coordinates.
    @p (x, y, z) is the world coordinates of a point
    @returns (x, y) in pixel coordinates'''
    return _half_screen_w+170*p[0], _half_screen_h-170*p[1]

def pix_to_w(p):
    '''Convert pixel coordinates to ode world coordinates.
    @p (x,y) is the pixel coordinates of a point in the screen
    @returns (x, y, 0) in world coordinates'''
    return (p[0]-_half_screen_w)/170.0, (_half_screen_h - p[1])/170.0, 0

def dist_to_pix(d):
    '''Convert ode world distance to pixel distance.
    @d is the distance in ode units
    @returns the distance in pixels'''
    return d * 170

def pix_to_dist(d):
    '''Convert pixel distance to ode world units distance.
    @d is the distance in pixels
    @returns the distance in ode units'''
    return d/170.0

def ccback(contactgroup, geom1, geom2):
    '''Collision callback. This function is called by space.collide to test if
    any objects in the space can be colliding'''
    mu = 0.0 # friction
    bounce = 0.0
    # test for our custom defined attributes
    if hasattr(geom1, 'mu'): mu += geom1.mu
    if hasattr(geom2, 'mu'): mu += geom2.mu
    if hasattr(geom1, 'bounce'): bounce += geom1.bounce
    if hasattr(geom2, 'bounce'): bounce += geom2.bounce

    contacts = ode.collide(geom1, geom2) # this is the real collision test
    for c in contacts:
        c.setBounce(bounce)
        c.setMu(mu)
        j = ode.ContactJoint(globals.ode_world, contactgroup, c)
        j.attach(geom1.getBody(), geom2.getBody())
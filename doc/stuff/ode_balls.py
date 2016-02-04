#!/usr/bin/env python
################################################################################
#                                                                              #
#   Pyode collission detection test                                            #
#   see the three tutorials in http://pyode.sourceforge.net/#starting          #
#   to understand what i'm doing here                                          #                                                               #
#                                                                              #
#   2008 - Felix del Rio fario@emergya.es                                      #
#                                                                              #
#   This program is free software: you can redistribute it and/or modify       #
#   it under the terms of the GNU General Public License as published by       #
#   the Free Software Foundation, either version 3 of the License, or          #
#   (at your option) any later version.                                        #
#                                                                              #
#   This program is distributed in the hope that it will be useful,            #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#   GNU General Public License for more details.                               #
#                                                                              #
#   You should have received a copy of the GNU General Public License          #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.      #
#                                                                              #
################################################################################

import pygame
import ode
import math
from random import random
from pygame.locals import *

running = 1

def coord(x,y):
    "Convert world coordinates to pixel coordinates."
    return 320+170*x, 480-170*y

def decoord(x, y):
    "Convert pixel coordinates to world coordinates."
    return (x-320)/170.0, (480 - y)/170.0

def cback(arg, geom1, geom2):
    '''space.collide callback.
The body method only guess what geometries are likely to be colliding we have
to call ode.collide in this method to get real collission information'''
    contacts = ode.collide(geom1, geom2)
    
    contactgroup, world = arg
    for c in contacts:
        c.setBounce(0.0) # decent bouncing
        c.setMu(0.0) # very little friction
        j = ode.ContactJoint(world, contactgroup, c)
        j.attach(geom1.getBody(), geom2.getBody())

def genBalls(world, space, number=100):
    '''Generates some balls for there to be action'''
    balls = [None] * number
    for i in xrange(0, number):
        balls[i] = ode.Body(world)
        m = ode.Mass()
        m.setSphere(800 + 100 * random(), 0.06)
        balls[i].setMass(m)
        
        balls[i].setPosition(decoord(640 * random(), 100 * random()) + tuple([0]))
        j = ode.Plane2DJoint(world)
        j.attach(balls[i], ode.environment)
        
        balls[i].geom = ode.GeomSphere(space, 0.06)
        balls[i].geom.setBody(balls[i])
        
        balls[i].color = (random() * 200, random() * 200, random() * 200)
    return balls

    

if __name__ == "__main__" :
    pygame.init()
    display = pygame.display.set_mode((640,480))
    
    world = ode.World() # world is the object that does the dynamic simulation
    world.setGravity((0,-9.81,0))
    
    space = ode.HashSpace() # space does the collision test and response
    #this jointgroup holds information about geometry points that are touching
    contactgroup = ode.JointGroup()
    
    floor = ode.GeomPlane(space, (0,1,0), 0) # geometry objects go in the space object
    wallr = ode.GeomPlane(space, (-1,0,0), -1.9)
    walll = ode.GeomPlane(space, (1,0,0), -1.9)
    ceil = ode.GeomPlane(space, (0,-1,0), -2.9)
    
    balls = genBalls(world, space) # bodies go in the world object
    
    pendulum = ode.Body(world)
    pendulum.mass = ode.Mass()
    pendulum.mass.setSphere(1130000, 0.12) # 100xlead density
    pendulum.setMass(pendulum.mass)
    
    pendulum.geom = ode.GeomSphere(space,0.12)
    pendulum.geom.setBody(pendulum)
    
    pendulum.setPosition(decoord(620, 250) + tuple([0]))
    
    join = ode.HingeJoint(world)
    join.attach(pendulum, ode.environment)
    join.setAnchor(decoord(320, 100) + tuple([0]))
    join.setAxis((0, 0, 1))
    
    j = ode.Plane2DJoint(world)
    j.attach(pendulum, ode.environment)
    
    fps = 60
    dt = 1.0/fps
    clk = pygame.time.Clock()
    while running:
        events = pygame.event.get()
        for e in events:
            if e.type==QUIT:
                running=False
            if e.type==KEYDOWN:
                if e.key==K_ESCAPE:
                    running=False
                elif e.key == K_SPACE:
                    for ball in balls: # move everything
                        force = (random()*2000 - 1000,
                                 random()*2000 - 1000,
                                 0)
                        ball.addForce(force)
                elif e.key == K_a:
                    nb = genBalls(world, space)
                    balls = balls + nb
                elif e.key == K_RIGHT:
                    pendulum.addForce((100000, 0, 0))
                elif e.key == K_LEFT:
                    pendulum.addForce((-100000, 0, 0))
        display.fill((255, 255, 255))
        
        display.fill((200, 200, 200), (280, 450, 80, 30))
        for ball in balls:
            x, y, z = ball.getPosition()
            pos = coord(x,y)
            pygame.draw.circle(display, ball.color, pos, 10)
            if pos[0] > 280 and pos[0] < 360 and pos[1] > 450 : #simulate a upgoing force in the center of the display
                force = (0, random()*50 + 200, 0)
                ball.addForce(force)
        
        x, y, z = pendulum.getPosition()
        pygame.draw.circle(display, (0, 0, 0), coord(x, y), 20)
        pygame.draw.line(display, (0, 0, 0), coord(x, y), (320, 100))        
        
        pygame.display.flip()
        
        contactgroup.empty() # clear the contacts list
        space.collide((contactgroup, world), cback)
        
        world.step(1.0/(clk.get_fps() or fps))
        clk.tick(fps)
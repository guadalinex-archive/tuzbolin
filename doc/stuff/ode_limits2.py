#!/usr/bin/env python
################################################################################
#                                                                              #
#   Pyode slider joint limits test                                             #
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
from pygame.locals import *

running = 1

if __name__ == "__main__" :
    pygame.init()
    display = pygame.display.set_mode((640,480))
    
    world = ode.World() # world is the object that does the dynamic symulation
    world.setGravity((0,-9.81,0))
    
    ball = ode.Body(world)
    ball.mass = ode.Mass()
    ball.mass.setSphere(11300, 0.12) # 100xlead density
    #ball.mass.setSphere(1500, 0.12)
    ball.setMass(ball.mass)
    
    hinge_body = ode.Body(world)
    
    ball.setPosition((1, 0, 0))
    slider = ode.SliderJoint(world)
    slider.attach(hinge_body, ode.environment)
    slider.setAxis((1, 0, 0))
    slider.setParam(ode.ParamVel, 0)
    slider.setParam(ode.ParamFMax, 100)
    
    join = ode.HingeJoint(world)
    join.attach(ball, hinge_body)
    join.setAnchor((0, 0, 0))
    join.setAxis((0, 0, 1))    
    join.setParam(ode.ParamVel, 0)
    join.setParam(ode.ParamFMax, 100)
    
    llimit = 0
    ulimit = 0
    
    pygame.font.init()
    font = pygame.font.Font(None, 24)
    
    fps = 60
    dt = 0.5/fps
    clk = pygame.time.Clock()
    while running:
        events = pygame.event.get()
        for e in events:
            if e.type==QUIT:
                running=False
            if e.type==KEYDOWN:
                if e.key==K_ESCAPE:
                    running=False
                elif e.key == K_RIGHT:
                    if ulimit:
                        slider.setParam(ode.ParamHiStop, ode.Infinity)
                        ulimit = 0
                    else:
                        slider.setParam(ode.ParamHiStop, 0.001)
                        ulimit = 1
                elif e.key == K_LEFT:
                    if llimit:
                        slider.setParam(ode.ParamLoStop, -ode.Infinity)
                        llimit = 0
                    else:
                        slider.setParam(ode.ParamLoStop, 0)                    
                        llimit = 1
        display.fill((255, 255, 255))
        
        x, y, z = ball.getPosition()
        x = 320+170*x
        y = 240-170*y
        pygame.draw.circle(display, (0, 0, 0), (x, y), 20)
        
        ox, oy, z = hinge_body.getPosition()
        ox = 320+170*ox
        oy = 240-170*oy
        pygame.draw.line(display, (0, 0, 0), (x, y), (ox, oy))
        
        pygame.draw.line(display, (0, 0, 128), (0, oy), (640, oy), 3)
        
        if ulimit:
            display.fill((128, 0, 0), (321, 235, 30, 10))
        
        if llimit:
            display.fill((128, 0, 0), (288, 235, 30, 10))
        
        display.blit(font.render('Pi * ' + str(join.getAngle() / math.pi), 1,
                                 (0, 0, 0)), (0, 0))
        pygame.display.flip()
        
        
        world.step(dt)
        clk.tick(fps)
    
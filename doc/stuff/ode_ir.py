#!/usr/bin/env python
################################################################################
#                                                                              #
#   Proof of Concepts of pygame, pyode and python-cwiid IR integration:        #
#                                                                              #
#   Python script that moves a pendulum using the slope defined by two points  #
#   reported by a wiimote                                                      #
#                                                                              #
#   Have fun!                                                                  #
#                                                                              #
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
import cwiid
from pygame.locals import *

STALE_THRESSHOLD = 1000
#wiimote_hwaddr = '' # Use your address to speed up the connection proccess
#wiimote_hwaddr = '00:19:1D:5D:5D:DC'
wiimote_hwaddr = '00:1F:C5:43:E1:29' # #1

running = 1
last_ok_time = -1000
last_distance, last_angle = 0, 0
dist_min, dist_max = cwiid.IR_X_MAX, 1
extent, angle = 0, 0
debug = ''

def cback(messages):
    '''Wiimote callback managing method
    Recieves a message list, each element is different, see the libcwiid docs'''
    global runing, last_distance, last_ok_time, dist_min, dist_max
    global angle, extent
    global debug
    for msg in messages:
        if msg[0] == cwiid.MESG_IR:
            point1, point2 = msg[1][0], msg[1][1]
            p1 = cwiid.IR_X_MAX - point1['pos'][0], point1['pos'][1]
            p2 = cwiid.IR_X_MAX - point2['pos'][0], point2['pos'][1]
            if point1 and point2:
                distance = math.sqrt((p2[0] - p1[0]) ** 2
                    + (p2[1] - p1[1]) ** 2)
                angle = math.atan2((p2[1] - p1[1]),
                                    (p2[0] - p1[0]))
                last_ok_time = pygame.time.get_ticks()

            distance = (distance + last_distance) / 2.0

            if distance < dist_min: dist_min = distance
            elif distance > dist_max: dist_max = distance

            extent = float(distance - dist_min) / float(dist_max - dist_min)
            debug += '\n' + str(extent) + " - " + str(angle)
        elif msg[0] == cwiid.MESG_ERROR:
            if msg[1] == cwiid.ERROR_DISCONNECT:
                runing = 0

def connect(wm_addr = ''):
    '''Connects and syncs with a wiimote
    wm_addr - Is a string representing the hwaddr of the wiimote we will try to
            connect, or none to try to connect with any discoverable device
            for example "00:19:1D:5D:5D:DC"'''
    # This could be done in a thread to allow pygame to draw while searching
    # but this is only a test
    try:
        return cwiid.Wiimote(wm_addr)
    except:
        print "Error conectando con wiimote " + str(wm_addr)

if __name__ == "__main__" :
    pygame.init()
    display = pygame.display.set_mode((640,480))
    
    world = ode.World() # world is the object that does the dynamic symulation
    world.setGravity((0,-9.81,0))
    
    ball = ode.Body(world)
    ball.mass = ode.Mass()
    #ball.mass.setSphere(1130000, 0.12) # 100xlead density
    #ball.mass.setSphere(1500, 0.12)
    ball.mass.setSphere(200, 0.12)
    ball.setMass(ball.mass)
    
    ball.setPosition((0, -1, 0))
    
    join = ode.HingeJoint(world)
    join.attach(ball, ode.environment)
    join.setAnchor((0, 0, 0))
    join.setAxis((0, 0, 1))
    #join.setParam(ode.ParamVel, 5)
    #join.setParam(ode.ParamFMax, 10)
    
    motor = 0
    
    llimit = 0
    ulimit = 0
    
    pygame.font.init()
    font = pygame.font.Font(None, 24)
    
    wm = None # our wiimote
    
    fps = 60
    dt = 0.5/fps
    clk = pygame.time.Clock()
    while running:
        if not wm:
            wm = connect(wiimote_hwaddr)
            if not wm:
                continue
            wm.rpt_mode = cwiid.RPT_IR | cwiid.RPT_BTN # | cwiid.RPT_STATUS
            wm.enable(cwiid.FLAG_MESG_IFC
                      #| cwiid.FLAG_NONBLOCK
                      | cwiid.FLAG_REPEAT_BTN)
            wm.mesg_callback = cback
            
            wm.led = 1

        #try: cback(wm.get_mesg())
        #except: pass
        
        events = pygame.event.get()
        for e in events:
            if e.type==QUIT:
                running=False
            if e.type==KEYDOWN:
                if e.key==K_ESCAPE:
                    running=False
                elif e.key == K_SPACE:
                    if motor:
                        join.setParam(ode.ParamVel, 0)
                        join.setParam(ode.ParamFMax, 0.5)
                        motor = 0
                    else:
                        join.setParam(ode.ParamVel, 75)
                        join.setParam(ode.ParamFMax, 10)
                        motor = 1
                elif e.key == K_RIGHT:
                    if ulimit:
                        join.setParam(ode.ParamHiStop, ode.Infinity)
                        ulimit = 0
                elif e.key == K_LEFT:
                    if llimit:
                        join.setParam(ode.ParamLoStop, -ode.Infinity)
                        llimit = 0
        
        display.fill((255, 255, 255))
        
        x, y, z = ball.getPosition()
        x = 320+170*x
        y = 240-170*y
        pygame.draw.circle(display, (0, 0, 0), (x, y), 20)
        pygame.draw.line(display, (0, 0, 0), (x, y), (320, 240))
        
        if angle != last_angle:
            join.setParam(ode.ParamHiStop, angle)
            join.setParam(ode.ParamLoStop, angle)
            ulimit, llimit = 1, 1
            
            
            
        last_angle = angle
        h = math.pi / 2.0
        if ulimit:
            ulx, uly = (100 * math.cos(-join.getParam(ode.ParamHiStop) + h),
                        100 * math.sin(join.getParam(ode.ParamHiStop) + h))
            pygame.draw.line(display, (0, 0, 128), (ulx + 320, uly + 240), (320, 240), 3)
        if llimit:
            llx, lly = (100 * math.cos(-join.getParam(ode.ParamLoStop) + h),
                        100 * math.sin(join.getParam(ode.ParamLoStop) + h))
            pygame.draw.line(display, (128, 0, 0), (llx + 320, lly + 240), (320, 240), 3)
        
        display.blit(font.render('Pi * ' + str(join.getAngle() / math.pi), 1,
                                (0, 0, 0)), (0, 0))
        display.blit(font.render('angle: ' + str(angle), 1, (0, 0, 0)), (0, 15))
        display.blit(font.render('extent: ' + str(extent), 1, (0, 0, 0)), (0, 30))
        for i in xrange(9):
            display.blit(font.render('rotation['+ str(i) + ']: ' + str(ball.getRotation()[-i]), 1, (0, 0, 0)), (0, 480 - 15*i))        
        
        i = 0
        d = debug.split('\n')
        for s in d:
            display.blit(font.render(s, 1, (0, 0, 0)), (300, i*15))
            i +=1
        
        if i:
            debug = '\n'.join(d[i/2:])
        
        pygame.display.flip()
        
        world.step(dt)
        clk.tick(fps)
    
    wm.close()

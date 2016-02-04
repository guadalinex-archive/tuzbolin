#!/usr/bin/env python
################################################################################
#                                                                              #
#   Proof of Concepts of pygame and python-cwiid IR pointer integration:       #
#                                                                              #
#   Python script that outputs to a window the points reported by the wiimote  #
#   ir sensor, trying to keep track of points which are at a determined        #
#   distance and tracking both their distance and the slope defined by them    #
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
import cwiid
import math
from random import random, randint
from pygame.locals import *

## Configuration
#wiimote_hwaddr = '' # Use your address to speed up the connection proccess
#wiimote_hwaddr = '00:19:1D:5D:5D:DC'
wiimote_hwaddr = '00:1F:C5:43:E1:29' # #1

## Globals
text_surf = 0
drawing = 0
last_point = 0
runing = 0
last_distance = 0
last_ok_time = -1000
font = None
dist_min, dist_max = cwiid.IR_X_MAX, 1
avg_dists = []
max_avg = 0

STALE_THRESSHOLD = 1000 # in ms

def quit():
    global runing
    runing = 0

def handle_events():
    '''Typical event handling via pygame'''
    for event in pygame.event.get():
        if event.type == QUIT:
            quit()
        elif event.type == KEYUP:
            if event.key == K_ESCAPE:
                quit()
            elif event.key == K_SPACE:
                canvas.fill((0, 0, 0), ((0, 0), canvas.get_size()))

def connect(wm_addr = ''):
    '''Connects and syncs with a wiimote
    wm_addr - Is a string representing the hwaddr of the wiimote we will try to
            connect, or none to try to connect with any discoverable device
            for example "00:19:1D:5D:5D:DC"'''
    global text_surf, wm, font
    if not text_surf: # cache an image with the text to show -> faster
        font = pygame.font.Font(None, 40)
        text_surf = font.render("Buscando Wiimote: presiona 1+2...", 1,
                                (0, 0, 0), (255, 255, 255))

    r = canvas.get_rect()
    tr = text_surf.get_rect()
    screen.blit(text_surf, (r.centerx - tr.centerx, r.centery - tr.centery))
    pygame.display.flip() # called now because cwiid.Wiimote is a blocking call
    
    # This could be done in a thread to allow pygame to draw while searching
    # but this is only a test
    try:
        return cwiid.Wiimote(wm_addr)
    except:
        print "Error conectando con wiimote " + str(wm_addr)

def get_points(data):
    '''Tells the real points from reflections, tries to get two valid points
    to compute a distance'''
    # checks the distance between every pair of points, and choose the
    # one nearest to the last distance

    if (pygame.time.get_ticks() - last_ok_time) > STALE_THRESSHOLD:
        screen.fill((255, 0, 0), (0, 0, 10, 10))
        dist_min, dist_max = cwiid.IR_X_MAX, 1
        return data[0], data[1]
    
    screen.fill((0, 255, 0), (0, 0, 10, 10))
    point1, point2 = (0, 0)
    point_distances = {}
    for p1 in data:
        for p2 in data:
            if p1 and p2 :
                d = math.sqrt((p2['pos'][0] - p1['pos'][0]) ** 2
                    + (p2['pos'][1] - p1['pos'][1]) ** 2)
                point_distances[d] = (p1, p2)
    
    last_dif = cwiid.IR_X_MAX
    nearest_key = 0
    keys = point_distances.keys()
    for k in keys:
        d = abs(abs(last_distance) - abs(k))
        if d < last_dif :
            last_dif = d
            nearest_key = k
            
    #print last_distance, keys, ' -> ', nearest_key, '(', last_dif, ')'
    
    if last_dif > (last_distance / 10):
        screen.fill((255, 255, 0), (0, 0, 10, 10))
        return None, None
    
    return point_distances[nearest_key]

def cback(messages):
    '''Wiimote callback managing method
    Recieves a message list, each element is different, see the libcwiid docs'''
    global max_avg, drawing, avg_dists, last_point, runing, last_distance, last_ok_time, dist_min, dist_max, font
    for msg in messages:
        if msg[0] == cwiid.MESG_IR:
            # msg is of the form (cwiid.MESG_IR, (((x, y), size) or None * 4))
            i = 0
            for p in msg[1]:
                if p:
                    canvas.blit(font.render(str(i), 1, (255, 255, 255)), p['pos'])
                    canvas.fill((255, 0, 0), (p['pos'], (p['size'], p['size'])))
                i+=1
            
            point1, point2 = get_points(msg[1])
            if point1 and point2:
                distance = math.sqrt((point2['pos'][0] - point1['pos'][0]) ** 2
                    + (point2['pos'][1] - point1['pos'][1]) ** 2)
                angle = math.atan2((point2['pos'][1] - point1['pos'][1]),
                                    (point2['pos'][0] - point1['pos'][0]))
                
                if last_point:
                    avg_dists += [math.sqrt((last_point[0] - point1['pos'][0]) ** 2 +
                        (last_point[1] - point1['pos'][1]) ** 2)]
                last_point = point1['pos']
                last_ok_time = pygame.time.get_ticks()
            
            distance = (distance + last_distance) / 2.0
            
            if distance < dist_min: dist_min = distance
            elif distance > dist_max: dist_max = distance
            
            extent = float(distance - dist_min) / float(dist_max - dist_min)
            
            canvas.fill((255, 255, 255), (0, 600, extent * cwiid.IR_X_MAX, 20))
            string = str(int(distance / 10.0) * 10.0)
            canvas.blit(font.render(string, 1, (255, 255, 255)), (0, 640))
            canvas.blit(font.render("Pi*"+str(angle / math.pi), 1, (255, 255, 255)), (30, 0))
            
            avg = 0            
            if len(avg_dists) >= 10:
                for i in avg_dists[-10:]:
                    avg += i
                avg /= 10.0
            canvas.blit(font.render("avg:"+str(avg), 1, (255, 255, 255)), (0, 30))
            if avg > max_avg or not(pygame.time.get_ticks() & 120):
                max_avg = avg
            canvas.blit(font.render("max avg:"+str(max_avg), 1, (255, 255, 255)), (0, 60))
            last_distance = distance
            
            if point1:
                pygame.draw.circle(canvas, (0, 255, 0), point1['pos'],
                                   point1['size'] * 4, point1['size'])
            if point2:
                pygame.draw.circle(canvas, (0, 255, 0), point2['pos'],
                                   point2['size'] * 4, point1['size'])

        elif msg[0] == cwiid.MESG_BTN:
            # msg is of the form (cwiid.MESG_BTN, cwiid.BTN_*)
            if msg[1] == cwiid.BTN_A:
                drawing = 1
            elif msg[1] == cwiid.BTN_B:
                canvas.fill((0, 0, 0))
        elif msg[0] == cwiid.MESG_ERROR:
            if msg[1] == cwiid.ERROR_DISCONNECT:
                global runing
                runing = 0
        #elif msg[0] == cwiid.MESG_STATUS:
        #    # msg is of the form (cwiid.MESG_BTN, { 'status' : value, ... })
        #    print msg[1]
            
    drawing = 0

if __name__ == '__main__':
    pygame.init()
    pygame.display.set_caption('Wiimote IR test')
    window = pygame.display.set_mode((cwiid.IR_X_MAX, cwiid.IR_Y_MAX), DOUBLEBUF)
    screen = pygame.display.get_surface()
    canvas = pygame.Surface(screen.get_size()) # persistent drawing here
    canvas = canvas.convert()
    
    wm = None # our wiimote
    clock = pygame.time.Clock()
    runing = 1
    while(runing):
        clock.tick(60)
        handle_events()
        if not wm:
            wm = connect(wiimote_hwaddr)
            if not wm:
                continue
            # each message will contain info about ir and buttons
            wm.rpt_mode = cwiid.RPT_IR | cwiid.RPT_BTN # | cwiid.RPT_STATUS
            # tell cwiid to use the callback interface and allways send button events
            wm.enable(cwiid.FLAG_MESG_IFC
                      #| cwiid.FLAG_NONBLOCK
                      | cwiid.FLAG_REPEAT_BTN)
            
            # specify wich function will manage messages AFTER the other settings
            wm.mesg_callback = cback
            
            # quick check on the wiimote
            print "Got Wiimote!"
            st = wm.state
            for e in st:
                print str(e).ljust(8), ">", st[e]
       
        screen.blit(canvas, (0, 0))
        canvas.fill((0, 0, 0))
        pygame.display.flip()
    
    if wm:
        pygame.time.delay(250)
        wm.close()
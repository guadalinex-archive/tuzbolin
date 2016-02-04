#!/usr/bin/env python
################################################################################
#                                                                              #
#   Proof of Concepts of pygame and python-cwiid accelerometer integration:    #
#                                                                              #
#   Python script that outputs to a window the stimated extent of a bar from   #
#   the accumulated accelerometer data from a wiimote                          #
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
wiimote_hwaddr = '00:1F:C5:43:E1:29' # wm#1

## Globals
text_surf = 0
font = None
extent = 0
runing = 0
last_rx = 0
last_ry = 0
last_rz = 0

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
    global text_surf, wm
    if not text_surf: # cache an image with the text to show -> faster
        global font
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


def cback(messages):
    '''Wiimote callback managing method
    Recieves a message list, each element is different, see the libcwiid docs'''
    global drawing, last_rx, last_ry, last_ry, runing, extent
    canvas.fill((0, 0, 0))
    for msg in messages:
        if msg[0] == cwiid.MESG_ACC:
            rx = relative_acc(msg[1][cwiid.X], cwiid.X)
            ry = relative_acc(msg[1][cwiid.Y], cwiid.Y)
            rz = relative_acc(msg[1][cwiid.Z], cwiid.Z)
            
            extent += last_ry - ry
            #extent = ry
            if extent > 1: extent = 1
            if extent < -1: extent = -1
            canvas.blit(font.render(str(extent), 1, (255, 255, 255)), (0, 0))
            canvas.blit(font.render(str(ry), 1, (255, 255, 255)), (0, 24))
            
            w = cwiid.IR_X_MAX / 2.0
            canvas.fill((255, 255, 255), (0, 600, w + w * extent, 20))
            
            
            last_rx = rx
            last_ry = ry
            last_rz = rz
        elif msg[0] == cwiid.MESG_BTN:
            # msg is of the form (cwiid.MESG_BTN, cwiid.BTN_*)
            pass
        elif msg[0] == cwiid.MESG_ERROR:
            if msg[1] == cwiid.ERROR_DISCONNECT:
                global runing
                runing = 0
        #elif msg[0] == cwiid.MESG_STATUS:
        #    # msg is of the form (cwiid.MESG_BTN, { 'status' : value, ... })
        #    print msg[1]
            
    drawing = 0
    
def relative_acc(acc, axis):
        '''Returns the percentage of acceleration on the given axis,
        applied the current calibration of the wiimote'''
        return (float(acc - cal[0][axis])
                / (cal[1][axis] - cal[0][axis]))

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
            wm.rpt_mode = cwiid.RPT_ACC | cwiid.RPT_BTN # | cwiid.RPT_STATUS
            # tell cwiid to use the callback interface and allways send button events
            wm.enable(cwiid.FLAG_MESG_IFC
                      #| cwiid.FLAG_NONBLOCK
                      | cwiid.FLAG_REPEAT_BTN)
            
            # specify wich function will manage messages AFTER the other settings
            wm.mesg_callback = cback
            
            cal = wm.get_acc_cal(cwiid.EXT_NONE)
            
            # quick check on the wiimote
            print "Got Wiimote!"
            st = wm.state
            for e in st:
                print str(e).ljust(8), ">", st[e]
       
        screen.blit(canvas, (0, 0))
        pygame.display.flip()
    
    if wm:
        pygame.time.delay(250)
        wm.close()
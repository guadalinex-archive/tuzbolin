#!/usr/bin/python
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
''' This module will hold the controlling logic and wiimote interaction. Game controlling mainly will be based on wiimote interface but basic keyboard controlling
is also possible. '''
import pygame
import cwiid
import ode
import math
from pygame.locals import *

import actors
import globals

class Controller:
    '''Base controller class'''
    def __init__(self):
        self.rot = 0
        self.slide = 0
        self.hard_turn = 0

    def control(self, actor, args):
        pass

class KeyController(Controller):
    '''Testing keyboard controller'''
    def __init__(self, keymap={'up': K_UP, 'down': K_DOWN,
                               'left': K_LEFT, 'right': K_RIGHT,
                               'boost': K_SPACE}):
        '''Testing keyboard controller
        @keymap a custom keymap can be specified as a dict with the following fields:
            up: for sliding the bar forward
            down: for sliding the bar backwards
            right: for rotate the bar clockwise
            left: for rotate the bar counter clockwise
            boost: for rotate the bar faster (unused)'''
        Controller.__init__(self)
        self.keymap = keymap
    def control(self, actor, args):
        '''Actor is a PenguinBar here'''
        k = pygame.key.get_pressed()
        self.hard_turn = 0
        keymap = self.keymap
        if k[keymap['left']]:
            self.rot = min((self.rot + 0.1, 1))
        elif k[keymap['right']]:
            self.rot = max((self.rot - 0.1, -1))
        if k[keymap['up']]:
            self.slide = min((self.slide + 0.03, 1))
        elif k[keymap['down']]:
            self.slide = max((self.slide - 0.03, -1))
        elif k[keymap['boost']]:
            self.hard_turn = 1
        
        actor.slide(self.slide)
        actor.rotate(self.rot)

class WiiController(Controller):
    '''Implements bar control using a wiimote. Here, we at first search for possible wiimotes around us or we can supply mac addresses as well. After connecting 
    wiimote controllers, we setup them, read different kind of messages from them and handle game controls and logic according to these messages. 
    There are three type of messages received from wiimote : accelerometer, button and infrared. More detail about Wiimotes is on the project wiki page. 
    All job is done asyncronously with callback function for each message type so we have controlling functions for each of them.
    Bar controlling options may vary according to configuration of the game.'''
    STAlE_DATA_TIME = 10 * 1000/globals.FPS # if it has more than 10 ticks old, is stale
    def __init__(self, player_number=0, btaddr=''):
        '''@btaddr the hardware address of the wiimote
        @player_number Identifier of this wiimote'''
        Controller.__init__(self)
        self.addr = btaddr
        self.number = player_number
        self.associated = False
        self.last_messages = []
        
        self.skip_tick = 0
        
        # acc dependant stuff
        self.last_acc_rx, self.last_acc_ry = 0, 0
        
        # ir dependant stuff
        self.last_distance = 0
        self.last_extent = 0
        self.last_ir_ok = 0
        # max/min distances of the points, will be guessed at playtime
        self.ir_dist_min, self.ir_dist_max = cwiid.IR_X_MAX, 1
        
        self.auto_calib = {'max':1, 'min':1}
        
    
    def try_associate(self):
        '''Tries to associate with the wiimote set to this controller or with
        any discoverable if none specified'''
        print "Put the wiimote in discoverable mode (1+2)"
        try:
            self.wm = cwiid.Wiimote(self.addr)
            if self.number:
                self.wm.led = 1 << (self.number - 1)
            return True
        except:
            return False
    
    def setup(self):
        '''Inits the connection parameters and does the communication setup to
        use the wiimote'''
        self.wm.rpt_mode = (cwiid.RPT_ACC
                            | cwiid.RPT_BTN)
                            #| cwiid.RPT_IR)
                            #| cwiid.RPT_STATUS)
        self.wm.enable(cwiid.FLAG_MESG_IFC
                       | cwiid.FLAG_REPEAT_BTN)
        
        self.wm.mesg_callback = self.callback
        
        self.calibration = self.wm.get_acc_cal(cwiid.EXT_NONE)
    
    def callback(self, messages):
        '''Used by the cwiid message interface, we use it to save a reference to
        the newest message list here'''
        for message in messages: # disconnect this wm
            if message[0] == cwiid.MESG_ERROR:
                if message[1] == cwiid.ERROR_DISCONNECT:
                    print "Wiimote ", self.number, " disconnected!!"
                else:
                    print "Error!!"
            elif message[0] == cwiid.MESG_ACC:
                self._acc_control(message[1], 0)
            elif message[0] == cwiid.MESG_IR:
                self._ir_control(message[1], 0)
            elif message[0] == cwiid.MESG_BTN:
                self._btn_control(message[1], 0)
                    
        self.last_messages = messages

    def associate(self):
        if self.try_associate():
            self.setup()
            self.associated = True

    def control(self, actor, arg):
        '''After determining association of the bars to control, handle action on bars. Each message type received from wiimote has different properties. And 
        all control is done according to that received data'''
        if not self.associated:
            self.associate()
        else:
            if self.hard_turn:
                actor.hard_turn(self.hard_turn)
            else:
                actor.rotate(self.rot)
            actor.slide(self.slide)
            #print "rot:", self.rot, " slide:", self.slide, " ht:", self.hard_turn

    def relative_acc(self, acc, axis):
        '''Returns the percentage of acceleration on the given axis,
        applied the current calibration of the wiimote'''
        return (float(acc - self.calibration[0][axis])
                / (self.calibration[1][axis] - self.calibration[0][axis]))

    def _acc_control(self, data, delta):
        '''Take action according to the last received message from accelerometers '''
        rx = self.relative_acc(data[cwiid.X], cwiid.X)
        ry = -self.relative_acc(data[cwiid.Y], cwiid.Y)
        
        x = (rx + self.last_acc_rx) / 2.0 # this smooths the movement
        d = self.last_acc_rx - rx
        if abs(d) > 1.5: # trayazo
            self.hard_turn = d
        else:
            self.hard_turn = 0
            if x > 1:x = 1
            elif x < -1:x = -1
            self.rot = x
            
        #if self.skip_tick and self.last_acc_ry:
        #    y = self.last_acc_ry - ry
        #    #print y
        #    self.slide -= y
        
        self.last_acc_rx = rx
        #self.last_acc_ry = ry
    
    def _get_points(self, data):
        '''Tells the real points from reflections, tries to get two valid points
        to compute a distance'''
        # checks the distance between every pair of points, and choose the
        # one nearest to the last distance
        # if we have no data or it's too old, return anything
        if (pygame.time.get_ticks() - self.last_ir_ok) > self.STAlE_DATA_TIME:
            self.skip_tick = True
            self.last_distance = 0
            if self.auto_calib['min']:
                self.ir_dist_min = cwiid.IR_X_MAX
            if self.auto_calib['max']:
                self.ir_dist_max = 1
            return data[0], data[1]
        
        point_distances = {}
        for p1 in data: # calculate distances for every pair of points
            for p2 in data:
                if p1 and p2 :
                    d = math.sqrt((p2['pos'][0] - p1['pos'][0]) ** 2
                        + (p2['pos'][1] - p1['pos'][1]) ** 2)
                    point_distances[d] = (p1, p2)
        
        # get the pair of points whose distance is nearest to the last tracked
        # distance
        last_dif = cwiid.IR_X_MAX
        nearest_key = 0
        keys = point_distances.keys()
        for k in keys:
            d = abs(abs(self.last_distance) - abs(k))
            if d < last_dif :
                last_dif = d
                nearest_key = k
                
        #print self.last_distance, keys, ' -> ', nearest_key, '(', last_dif, ')'
        
        # if there has been a great change we might have lost sight of one point
        # and we are tracking a point and its reflection
        if last_dif > (self.last_distance / 10):
            return None, None
        
        return point_distances[nearest_key]

    def _ir_control(self, data, delta):
        '''Take action according to the last received message from infrared. At first, try to catch valid points from wiimote by _get_points() function.
        Then, determine extent of values to apply according to distance and reflections of the wiimote.
        '''
        #actor.debug = ''
        
        point1, point2 = self._get_points(data)
        
        if not (point1 and point2):
            #print 'Not enought ir sources: ', data
            return
        
        p1 = point1['pos']
        p2 = point2['pos']
        
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        d = math.sqrt(dx ** 2 + dy ** 2)
        
        # update the max/min distance, to keep the extent changing relative to
        # the player movement
        if self.auto_calib['min'] and d < self.ir_dist_min:
            self.ir_dist_min = d
        elif self.auto_calib['max'] and d > self.ir_dist_max:
            self.ir_dist_max = d
        
        self.skip_tick = not self.last_distance # if we just adquired the points, wait
        
        extent = (d - self.ir_dist_min)/ (float(self.ir_dist_max - self.ir_dist_min) + 0.001) #calculated the value according to distance and reflections 
        
        self.last_distance = d
        
        extent = (extent + self.last_extent) / 2.0
        self.last_extent = extent
        
        self.last_ir_ok = pygame.time.get_ticks()
    
    def _btn_control(self, button, delta):
        '''Take action according to the last received message from buttons. '''
        #'B' button on the wiimote increases the bar speed
        bar_speed = 0.01
        self.hard_turn = 0
        if button & cwiid.BTN_A:
            self.hard_turn = 1
        if button & cwiid.BTN_B:
            bar_speed = 0.1
        if button & cwiid.BTN_2:
            self.ir_dist_min = self.last_distance
            self.auto_calib['min'] = 0
        if button & cwiid.BTN_1:
            self.ir_dist_max = self.last_distance
            self.auto_calib['max'] = 0
        if button & cwiid.BTN_UP:
            self.slide = min((self.slide + bar_speed, 1))
        if button & cwiid.BTN_DOWN:
            self.slide = max((self.slide - bar_speed, -1))
        #if button & cwiid.BTN_A:
        #    b = actors.Ball()
        #    globals.balls.add(b)
        #    b.kickoff()

class IRController(Controller):
    '''Implements bar control using a single wiimote and several IR sources.
    to control several bars at once.
    The order in wich the actors are created (and the controller is added)
    is determinant if controller_secuence is not set'''
    def __init__(self, wiimote_number=0, btaddr='', calibration = False, controller_secuence=False):
        '''
        @btaddr the hardware address of the wiimote
        @calibration Two element tuple of (min, max) distance between ir points,
        in pixels
        @controller_secuence is the order in wich the actors will be set to be controlled'''
        Controller.__init__(self)
        self.addr = btaddr
        self.number = wiimote_number
        self.led_on = 0
        if calibration:
            self.max = [calibration[1]] * 2
            self.min = [calibration[0]] * 2
            self.auto_calib = False
        else:
            self.auto_calib = True
            self.max = [0, 0]
            self.min = [cwiid.IR_X_MAX, cwiid.IR_X_MAX]
        self.cal_timeout = 0
        
        self.slide = [0, 0]
        self.rot = [0, 0]
        self.hard_turn = [0, 0]
            
        self.last_extent = [0, 0]
        self.last_angle = [0, 0]
        
        self.associated = False
        self.last_messages = []
        self.last_points = [(None, None), (None, None)]
        self.last_num_points = 0
        self.points_ordered = False
        
        self.controller_secuence = controller_secuence
        self.actor_x_points = {} # hash(actor) x 0 or 1 (set of points)

    def try_associate(self):
        '''Tries to associate with the wiimote set to this controller or with
        any discoverable if none specified'''
        print "Put the wiimote in discoverable mode (1+2)"
        try:
            self.wm = cwiid.Wiimote(self.addr)
            return True
        except:
            return False
    
    def setup(self):
        '''Inits the connection parameters and does the communication setup to
        use the wiimote'''
        self.wm.rpt_mode = (cwiid.RPT_IR)
        self.wm.enable(cwiid.FLAG_MESG_IFC)
        self.wm.mesg_callback = self.callback
        if self.number:
            self.wm.led = 1 << self.number
            self.led_on = 1


    def callback(self, messages):
        '''cwiid callback, state fetching and such'''
        for message in messages: # disconnect this wm
            if message[0] == cwiid.MESG_ERROR:
                if message[1] == cwiid.ERROR_DISCONNECT:
                    print "Wiimote disconnected!!"
                else:
                    print "Error!!"
            if message[0] == cwiid.MESG_IR:
                i = 0
                controls = self.get_controls(message[1])
                for p in controls:
                    if not (p[0] and p[1]):
                        #print 'Not enought ir sources: ', points
                        continue
                    self.slide[i] = self.get_extent(p, i)
                    self.rot[i] = self.get_angle(p, i)
                    
                    i += 1
                self.last_points = controls
    
    def by_x(self, p1, p2):
        '''orders points by x-cordinate (inverse)'''
        if p1 and p2:
            return p1[0] - p2[0]
        else:
            if p1:
                return -1
            elif p2:
                return 1
            else:
                return 0
            
    
    def get_controls(self, points):
        '''Tries to tell apart two sets of points one pair for each control'''
        # TODO do something useful here like on get_points
        pos = []
        num = 0
        for p in points:
            if p:
                pos.append(p['pos'])
                num += 1
            else: pos.append(None)
        
        self.points_ordered &= self.last_num_points == num
        self.points_ordered &= not self.cal_timeout
        #print self.last_num_points, " =? ", num
        if not self.points_ordered:
            if self.cal_timeout: # if we are counting
                self.cal_timeout -= 1
                if self.cal_timeout: # not finished yet
                    return
            else:
                self.cal_timeout = 10
                return
            #print 'before: ', pos        
            #pos.sort(self.by_x)
            self.points_ordered = True
            if self.auto_calib:
                self.max = [0, 0]
                self.min = [cwiid.IR_X_MAX, cwiid.IR_X_MAX]
            #print 'after: ', pos
            
        self.last_num_points = num
        return [(pos[0], pos[1]), (pos[2], pos[3])]
    
    def get_extent(self, points, controller):
        '''Obtains the variation on the bar extent'''
        if not (points[0] and points[1]):
            #print 'Not enought ir sources: ', points
            if self.auto_calib:
                self.max = [0, 0]
                self.min = [cwiid.IR_X_MAX, cwiid.IR_X_MAX]
            return
        p1 = points[0]
        p2 = points[1]
        
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        d = math.sqrt(dx ** 2 + dy ** 2)
        
        # update the max/min distance, to keep the extent changing relative to
        # the player movement
        if self.auto_calib and d < self.min[controller]:
            self.min[controller] = d
        elif self.auto_calib and d > self.max[controller]:
            self.max[controller] = d
       
        #calculated the value according to distance and reflections 
        extent = (d - self.min[controller]) / \
                 (float(self.max[controller] - self.min[controller]) + 0.001)
        
        extent = (extent + self.last_extent[controller]) / 2.0
        self.last_extent[controller] = extent
        
        return extent
    
    def get_angle(self, points, controller):
        '''returns the angle [-pi, pi] that is the slope of the line formed by
        the given points'''
        angle =  math.atan2((points[1][1] - points[0][1]),
                            (points[1][0] - points[0][0]))
        return (2.0 * angle/math.pi)
    
    def associate(self):
        '''Tries to associate with the assigned wiimote'''
        if self.try_associate():
            self.setup()
            self.associated = True
            
    def control(self, actor, arg):
        '''After determining association of the bars to control, handle action on bars. Each message type received from wiimote has different properties. And 
        all control is done according to that received data'''
        if not self.associated:
            self.associate()
        else:
            if not self.led_on:
                self.number = actor.team
                self.wm.led = 1 << self.number
                self.led_on = 1
            
            if self.actor_x_points.has_key(hash(actor)):
                controller = self.actor_x_points[hash(actor)]
                actor.rotate(self.rot[controller])
                actor.slide((self.slide[controller] * 2.0) - 1.0)
            else:
                if not self.controller_secuence:
                    lens = [0, 0]
                    for i in self.actor_x_points.values():
                        lens[i] += 1
                    if lens[0] > lens[1]:
                        self.actor_x_points[hash(actor)] = 1
                    else:
                        self.actor_x_points[hash(actor)] = 0
                else:
                    n = len(self.actor_x_points) % len(self.controller_secuence)
                    self.actor_x_points[hash(actor)] = self.controller_secuence[n]

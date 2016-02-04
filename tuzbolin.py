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

'''Main game module, will load everything and hold the main loop'''

import pygame
import sys
import ode
import yaml
from pygame.locals import *
from random import random

import globals
import world
import actors
import control

_running = 1

def startup():
    '''Inits everything and loads what's needed to start playing
    @bars, @balls and @assets are sprite groups that are going to implement various actions on included sprite instances like add, remove, collision detection etc.   
    '''
    # init playfield (4 walls, consist of ode.GeomPlane instances as they don't move , just hold other objects between them. )
    dwidth = -world.pix_to_dist(globals.FIELD_SIZE[0] / 2.0)
    dheight = -world.pix_to_dist(globals.FIELD_SIZE[1] / 2.0)
    north = ode.GeomPlane(globals.ode_space, (0, -1, 0), dheight)
    south = ode.GeomPlane(globals.ode_space, (0, 1, 0), dheight)
    west = ode.GeomPlane(globals.ode_space, (1, 0, 0), dwidth)
    east = ode.GeomPlane(globals.ode_space, (-1, 0, 0), dwidth)
    
    # goals: two pygame rects we will test against the ball on its update method
    goal_left = pygame.Rect((0, 0), globals.GOAL_SIZE)
    goal_left.center = (globals.FIELD_TOP_LEFT[0],
                        globals.FIELD_TOP_LEFT[1] + globals.FIELD_SIZE[1] / 2)
    goal_right = pygame.Rect((0, 0), globals.GOAL_SIZE)
    goal_right.center = (globals.FIELD_TOP_LEFT[0] + globals.FIELD_SIZE[0],
                         globals.FIELD_TOP_LEFT[1] + globals.FIELD_SIZE[1] / 2)
    globals.goals = [goal_left, goal_right]
    
    # set up one sprite group for the bars, we add it to the globals
    globals.bars = pygame.sprite.RenderUpdates()
    
    globals.controllers = []
    
    # create as many IRController as told on the config file
    for i in xrange(globals.config['num_wiimotes']):
        globals.controllers.append(control.IRController(btaddr=globals.config['wm'][i],
                                                        controller_secuence=[0,0,0,0])) #TODO specify sequence
    # fill every other controller with keycontrollers
    for i in xrange(4 - globals.config['num_wiimotes']):
        globals.controllers.append(control.KeyController())
    
    numbars = 8
    bar_x_teams = [0, 0, 1, 0 ,1 ,0 ,1 ,1]
    
    # align penguin bars according to the distances between them. we determine that according to the number of the bars, which are constant.
    bars_separation = globals.FIELD_SIZE[0] / numbars
    bars_start = globals.FIELD_TOP_LEFT[0]
    
    # Create bars with a position data at where it will be drawn, number of penguins on the bar, controller that direct actions on the bar, and team id of the bar
    for i in xrange(numbars):
        actor = actors.PenguinBar(bars_start + bars_separation * i,
                                  globals.config['penguins_x_bars'][i],
                                  globals.controllers[globals.config['controller_order'][i]],
                                  bar_x_teams[i])
        globals.bars.add(actor)
        
        bimx = (actor.rect.x +
                (actor.sprite_size -
                 actors.PenguinBar.bar_image.get_rect().w) / 2.0)
        field_bg.blit(actors.PenguinBar.bar_image,
                      (bimx, actor.rect.y))
    
    # scores: the index of a team should be the same index of his goal
    globals.score = [0, 0]
    # An effects layer, to control public, scoreboards, etc...
    globals.assets = pygame.sprite.RenderUpdates()
    globals.assets.add(actors.ScoreBoard())
    if globals.config['game']['time']:
        globals.assets.add(actors.Timer((400, 100)))
    # another for the balls (could be more than one?), balls are also in globals
    globals.balls = pygame.sprite.RenderUpdates()
    actors.Ball.extra_ball()
    
    # add dynamic public actors
    globals.assets.add(actors.Public('resources/images/tuzbolo.png',
                                    (480, 45), 1, 1000, 4))
    
    # kickoff! not needed but nice
    for ball in globals.balls:
        ball.kickoff()

def process_events():
    """Processess mouse and kb events for the main ui"""
    global _running
    for event in pygame.event.get():
        if event.type == QUIT:
            _running = 0
        elif event.type == KEYUP:
            if event.key == K_ESCAPE: # exit the game
                _running = 0
            if event.key == K_r: # reinit the ball position
                for ball in globals.balls:
                    ball.kickoff()
            if event.key == K_a: # extra ball
                actors.Ball.extra_ball()
            if event.key == K_o: # raise fps limit (debug)
                globals.FPS += 1
                print globals.FPS
            if event.key == K_p: # lower fps limit (debug)
                globals.FPS -= 1
                print globals.FPS


def main_loop():
    '''Main game plays in here. First determine user actions, then run game in the given state such as playing, paused, credits, victory etc..  '''
    c = pygame.time.Clock()
    # local functions and variables are faster to call in a loop, so we cache
    # them before looping
    fps = globals.FPS
    bars = globals.bars
    balls = globals.balls
    assets = globals.assets
    w_step = globals.ode_world.step
    s_collide = globals.ode_space.collide
    cgroup = ode.JointGroup()
    collission_callback = world.ccback
    first_loop = 1
    max_goals = globals.config['game']['goals']
    globals.time_limit = 0
    new_match_time = 0
    state = globals.ST_WAITING
    while _running:
        process_events()
        if state == globals.ST_PLAYING:
            state = playing(c, fps, bars, balls, assets, cgroup,
                            s_collide, w_step, collission_callback, max_goals)
        elif state == globals.ST_END: # game end
            if not new_match_time:
                new_match_time = pygame.time.get_ticks() + globals.config['game']['wait_time']
                    
            display.blit(field_bg, (0, 0))
            text = "\xa1Habeis empatado!"
            if globals.score[0] > globals.score[1]:
                text = "\xa1Victoria\n    del equipo Morado!"
            elif globals.score[0] < globals.score[1]:
                text = "\xa1Ha ganado\n    el equipo Naranja!"

            globals.font.render(display, text,
                                ((globals.DISPLAY_SIZE[0] - globals.font.length(text))/2, 150), 1)
            globals.font.render(display, "El siguiente partido", (100, 350), 1)
            globals.font.render(display, "empieza en " +
                                str((new_match_time - pygame.time.get_ticks())/1000) +
                                " segundos",
                                (125, 400), 1)
            pygame.display.update()
            
            if pygame.time.get_ticks() > new_match_time:
                new_match_time = 0
                state = globals.ST_PLAYING
                globals.score = [0, 0]
                globals.time_limit = 0
                display.blit(field_bg, (0, 0))
                pygame.display.update()
        elif state == globals.ST_WAITING: # not all controllers are ready to play
            display.blit(field_bg, (0, 0))
            globals.font.render(display, "Esperando jugadores", (200, 250), 1)
            globals.font.render(display, "Presione 1 y 2", (100, 350), 1)
            globals.font.render(display, "en todos los mandos", (150, 400), 1)
            pygame.display.update()
            ready = True
            for con in globals.controllers:
                if hasattr(con, 'associated'):
                    if not con.associated:
                        try:
                            con.associate()
                            ready &= con.associated
                        except:
                            print sys.exc_type, ": ", sys.exc_value
                    elif hasattr(con, 'last_num_points'):
                        ready &= con.last_num_points >= 2
            
            if ready:
                display.blit(field_bg, (0, 0))
                pygame.display.update()
                state = globals.ST_PLAYING
    
    # close every wiimote connection before exiting
    for c in globals.controllers:
        if hasattr(c, 'wm'):
            c.wm.close()


def playing (c, fps, bars, balls, assets, cgroup, s_collide, w_step, collission_callback, max_goals):
    '''Game state actions for playing state,
    arguments are the local variables from the main loop variables from'''
    # clear
    bars.clear(display, field_bg)
    balls.clear(display, field_bg)
    assets.clear(display, field_bg)
    #display.blit(field_bg, (0, -2.0))
    
    # updating
    bars.update(0)
    balls.update(0)
    assets.update(0)
    cgroup.empty()
    s_collide(cgroup, collission_callback)
    w_step(1.0/(c.get_fps() or fps))
    
    # and drawing
    dirty = []
    dirty += balls.draw(display)
    dirty += bars.draw(display)
    dirty += assets.draw(display)
    
    # === DEBUG
    # fps
    if globals.fps:
        globals.debug_font.render(display, str(c.get_fps()), (0, 0))
        dirty += [pygame.Rect((0, 0, 150, 15))]

    if globals.debug:
        # points
        srf = pygame.Surface((256, 192)).convert()
        color = [255, 0, 0]
        for cont in globals.controllers:
            if hasattr(cont, 'last_points'):
                display.blit(debug_points(srf, cont.last_points, tuple(color)),
                             (globals.DISPLAY_SIZE[0] - 256, 0))
                color.insert(color.pop(), 0)
    
        dirty += [pygame.Rect((globals.DISPLAY_SIZE[0] - 256, 0, 256, 192))]
        
        a = 0
        for r in dirty:
            a += r.w * r.h
            #display.fill((255, 0, 0, 0), r)
            
        globals.debug_font.render(display, str(a), (0, 15))
        
#        for bar in globals.bars:
#            for body in bar.bodies:
#                bpos = body.getPosition()
#                dpos = world.w_to_pix(bpos)
#                pygame.draw.circle(display, (255, 0, 0), dpos, 16)
    # ======
    
    pygame.display.update(dirty)
    #pygame.display.update() # clear all the screen
    
    # ====== End game conditions
    if globals.time_limit:
        if pygame.time.get_ticks() > globals.time_limit:
            return globals.ST_END
    else:
        globals.time_limit = globals.config['game']['time'] + pygame.time.get_ticks()
    if max(globals.score) >= max_goals:
        return globals.ST_END        
    # ======
    
    c.tick(globals.FPS)
    return globals.ST_PLAYING

def debug_points(srf, points, color=(255, 0, 0)):
    '''Draws the view of a wiimote camera, given the last points registered by
    the sensor
    @srf - The surface to draw the points to
    @points - The points to draw
    @color - of the points'''
    #print points
    i = 1
    for cont in points:
        if cont:
            for point in cont:
                if point:
                    globals.debug_font.render(srf, str(i),
                                        (point[0]/4, point[1]/4, 2, 2))
                    srf.fill(color, (point[0]/4, point[1]/4, 2, 2))
                    i += 1
    return srf

if __name__ == '__main__':
    # TODO parse command line options
    pygame.init()
    pygame.mouse.set_visible(0)
        
    pygame.display.set_caption('Tuzbolin')
    pygame.display.set_icon(pygame.image.load('resources/images/tuzbolin.png'))
    
    display = pygame.display.set_mode(globals.DISPLAY_SIZE,
                                      globals.DISPLAY_FLAGS)
    
    field_bg = pygame.image.load('resources/images/fondo.jpg')
    ##play sound in infinite loop
    if globals.sound:
        pygame.mixer.init()
        if globals.config['ambient_sound']:
            actors.ambience_channel.play(actors.ambience_sound,-1)
    # init game font
    globals.font = actors.Font(font='resources/Domestic_Manners.ttf', size=52, 
                               color=(255, 175, 0), bg_color=None, bold=1)
    # init debug font
    globals.debug_font = actors.Font()
    
    # prepare the simulation
    world.init_ode()
    
    # init the game variables
    startup()
    
    # paint the full background once
    display.blit(field_bg, (0, 0))
    globals.font.render(display, "Esperando a los jugadores", (200, 300), 1)
    globals.font.render(display, "Presionen 1+2 en todos los mandos", (100, 350), 1)
    pygame.display.update()
    
    # start the game!
    main_loop()
    

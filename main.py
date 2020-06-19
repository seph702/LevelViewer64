import pyglet
from pyglet.gl import *
import math
import os
import time
from pathlib import Path
import ctypes
import pickle

from parsers.level_script_parser import LevelScript, LevelGeo, LevelGeoDisplayList, Area, Obj, WaterBox
from parsers.level_fixes import get_extra_scale
from parsers.geo_parser import Geo, GeoDisplayList, Animation
from parsers.model_parser import Vertex, Vtx, Gfx, GfxDrawList, Light, RenderSettings
from parsers.movtex_tri_parser import Movtex_Tri

import util_math
from skybox import Skybox
from groups import TextureEnableGroup, TextureBindGroup, Layer0Group, Layer1Group, Layer2Group, Layer3Group, Layer4Group, Layer5Group, Layer6Group, Layer7Group, RenderSettingsGroup
from camera import FirstPersonCamera
from geometry import Geometry
#from menus import Button, Slider, Menu, PauseMenu, IntroMenu, MainPauseMenu, OptionsMenu, LevelSelectMenu
#from game_window import GameWindow


###############
### CLASSES ###
###############


class Slider():
    """( center_x, center_y ) is the position of the center of the slider object.  Text is the text that will be display slightly above and to the left of the slider itself.  min_val and max_val are the text values that should be displayed at both ends of the slider.  The colours are, in order, text colour, left half of non-hovered bar, right half of non-hovered bar, left half of hovered bar, right half of hovered bar."""
    def __init__( self, default_val, min_val, max_val, window_width, window_height, center_x = 1/2, center_y=1/2, width=1/2, height=1/16, text=None, font=None, text_font_size=25, val_font_size=18, num_digits=0, colors=[ [ 255, 255, 255, 255 ], [ 0, 120, 212, 255 ], [ 144, 144, 144, 255 ], [ 0, 90, 158, 255 ], [ 208, 208, 208, 255 ] ], batch=None, foreground_group=None, background_group=None ):
        self.batch = batch
        self.foreground_group = foreground_group
        self.background_group = background_group
        self.window_width = window_width
        self.window_height = window_height
        self.center_x_ratio = center_x
        self.center_y_ratio = center_y
        self.center_x = self.center_x_ratio * self.window_width
        self.center_y = self.center_y_ratio * self.window_height
        self.width_ratio = width
        self.height_ratio = height
        self.original_width = self.width_ratio * self.window_width
        self.original_height = self.height_ratio * self.window_height
        self.width = self.width_ratio * self.window_width
        self.height = self.height_ratio * self.window_height
        self.resize_width_ratio = self.original_width / self.width
        self.resize_height_ratio = self.original_height / self.height
        self.text = text
        self.font = font
        self.font_x = self.center_x - self.width / 2
        self.font_y = self.center_y + self.height / 2
        self.text_font_size = text_font_size
        self.text_color = colors[ 0 ]
        self.left_half_color = colors[ 1 ]
        self.right_half_color = colors[ 2 ]
        self.left_half_hovered_color = colors[ 3 ]
        self.right_half_hovered_color = colors[ 4 ]
        self.left_edge = self.center_x - 3 * self.width / 8 ## Corresponds to where the slider will stop at self.min_val
        self.right_edge = self.center_x + 3 * self.width / 8 ## Corresponds to where the slider will stop at self.max_val
        self.val_text_center_x = self.center_x - 7 * self.width / 16
        self.val_text_center_y = self.center_y - self.height / 4
        self.val_font_size = val_font_size
        ## The top and bottom of the hover region are aligned with the top and bottom of the sliding circle.
        self.hover_top = self.val_text_center_y + self.height / 5
        self.hover_bottom = self.val_text_center_y - self.height / 5
        self.min_val = min_val
        self.max_val = max_val

        self.num_digits = num_digits
        if self.num_digits != 0:
            self.current_val = round( float( default_val ), self.num_digits )
        else:
            self.current_val = int( default_val )

        self.slider_current_x = self.left_edge + ( self.current_val - self.min_val ) / ( self.max_val - self.min_val ) * ( 3 * self.width / 4 )
        self.left_bar = pyglet.shapes.Line( self.left_edge, self.val_text_center_y, self.slider_current_x, self.val_text_center_y, self.height / 10, self.left_half_color[ : 3 ], batch=self.batch, group=self.background_group )
        self.right_bar = pyglet.shapes.Line( self.slider_current_x, self.val_text_center_y, self.right_edge, self.val_text_center_y, self.height / 10, self.right_half_color[ : 3 ], batch=self.batch, group=self.background_group )
        self.sliding_circle = pyglet.shapes.Circle( self.slider_current_x, self.val_text_center_y, self.height/5, color=self.left_half_color[ : 3 ], batch=self.batch, group=self.foreground_group )
        self.hover = False
        self.label = pyglet.text.Label( self.text, font_name=self.font, font_size=self.text_font_size, x=self.font_x, y=self.font_y, anchor_x='left', anchor_y='top', color=self.text_color, batch=self.batch, group=foreground_group )
        self.val_label = pyglet.text.Label( str( self.current_val ), font_name=self.font, font_size=self.val_font_size, x=self.val_text_center_x, y=self.val_text_center_y, anchor_x='center', anchor_y='center', color=self.text_color, batch=self.batch, group=foreground_group )


    def check_hover( self, mouse_x, mouse_y ):
        if self.left_edge < mouse_x < self.right_edge and self.hover_bottom < mouse_y < self.hover_top:
            self.hover = True
            self.left_bar.color = self.left_half_hovered_color[ : 3 ]
            self.right_bar.color = self.right_half_hovered_color[ : 3 ]
            self.sliding_circle.color = self.left_half_hovered_color[ : 3 ]
            return True
        else:
            self.hover = False
            self.left_bar.color = self.left_half_color[ : 3 ]
            self.right_bar.color = self.right_half_color[ : 3 ]
            self.sliding_circle.color = self.left_half_color[ : 3 ]
            return False


    def check_click( self, mouse_x, mouse_y ):
        self.change_slider_pos( mouse_x )
        self.set_current_val()
        return True


    def change_slider_pos( self, x ):
        self.slider_current_x = max( x, self.left_edge )
        self.slider_current_x = min( self.slider_current_x, self.right_edge )
        self.left_bar.x2 = self.slider_current_x * self.resize_width_ratio
        self.right_bar.x = self.slider_current_x * self.resize_width_ratio
        self.sliding_circle.x = self.slider_current_x * self.resize_width_ratio


    def set_current_val( self ):
        if self.num_digits != 0:
            self.current_val = round( self.min_val + ( ( self.slider_current_x - self.left_edge ) / ( self.right_edge - self.left_edge ) ) * ( self.max_val - self.min_val ), self.num_digits )
        else:
            self.current_val = int( self.min_val + ( ( self.slider_current_x - self.left_edge ) / ( self.right_edge - self.left_edge ) ) * ( self.max_val - self.min_val ) )

        self.val_label.text = str( self.current_val )


    def set_release( self ):
        pass


    def on_screen_resize( self, width, height ):
        ## In this case, the width and height of the screen has changed.  So to check that a mouse is hovering over a button, we need to update self.left, self.right, self.bottom, and self.top since these no longer corresopnd to where the button actually renders on screen.
        ## Note, we don't have to change the vertex_lists or anything because we haven't changed resolution.  So the screen will still render properly, however mouse coordinates are affected, so we only have to update the internal button position for hover and click checks.
        self.window_width = width
        self.window_height = height
        self.center_x = self.center_x_ratio * self.window_width
        self.center_y = self.center_y_ratio * self.window_height
        self.width = self.width_ratio * self.window_width
        self.height = self.height_ratio * self.window_height
        self.resize_width_ratio = self.original_width / self.width
        self.resize_height_ratio = self.original_height / self.height
        self.left_edge = self.center_x - 3 * self.width / 8 ## Corresponds to where the slider will stop at self.min_val
        self.right_edge = self.center_x + 3 * self.width / 8 ## Corresponds to where the slider will stop at self.max_val
        self.val_text_center_y = self.center_y - self.height / 4
        self.hover_top = self.val_text_center_y + self.height / 5
        self.hover_bottom = self.val_text_center_y - self.height / 5
        self.slider_current_x = self.left_edge + ( self.current_val - self.min_val ) / ( self.max_val - self.min_val ) * ( 3 * self.width / 4 )
        self.left_bar.x = self.left_edge * self.resize_width_ratio
        self.left_bar.x2 = self.slider_current_x * self.resize_width_ratio
        self.right_bar.x = self.slider_current_x * self.resize_width_ratio
        self.right_bar.x2 = self.right_edge * self.resize_width_ratio
        self.sliding_circle.x = self.slider_current_x * self.resize_width_ratio



class Button():
    """( center_x, center_y ) is the position of the center of the button.  width and height are as expected.  Text is text that will be displayed.  Colors takes a list of four colours, each a list with 4 values: RGBA.  The list of colours corresponds to: text colour which defaults to ( 255, 255, 255, 255 ), button colour which defaults to ( 0, 120, 212, 255 ), button_hover colour = ( 16, 110, 190, 255 ), and button_click colour = ( 0, 90, 158, 255 )."""
    def __init__( self, window_width, window_height, center_x=1/2, center_y=1/2, width=1/8, height=1/16, text=None, font=None, font_size=16, colors=[ [ 255, 255, 255, 255 ], [ 0, 120, 212, 255 ], [ 16, 110, 190, 255 ], [ 0, 90, 158, 255 ] ], batch=None, foreground_group=None, background_group=None, multiline=False ):
        self.batch = batch
        self.foreground_group = foreground_group
        self.background_group = background_group
        self.window_width = window_width
        self.window_height = window_height
        self.center_x_ratio = center_x
        self.center_y_ratio = center_y
        self.center_x = self.center_x_ratio * self.window_width
        self.center_y = self.center_y_ratio * self.window_height
        self.width_ratio = width
        self.height_ratio = height
        self.width = self.width_ratio * self.window_width
        self.height = self.height_ratio * self.window_height
        self.multiline = multiline
        self.text = text
        self.font = font
        self.text_color = colors[ 0 ]
        self.button_color = colors[ 1 ]
        self.button_hover_color = colors[ 2 ]
        self.button_click_color = colors[ 3 ]
        self.font_size = font_size
        self.left = self.center_x - self.width / 2
        self.right = self.center_x + self.width / 2
        self.bottom = self.center_y - self.height / 2
        self.top = self.center_y + self.height / 2
        self.hover = False
        self.click = False
        if self.multiline:
            self.label = pyglet.text.Label( self.text, font_name=self.font, font_size=self.font_size, x=self.center_x, y=self.center_y, anchor_x='center', anchor_y='center', color=self.text_color, batch=self.batch, group=foreground_group, multiline=self.multiline, width=self.width, align='center' )
        else:
            self.label = pyglet.text.Label( self.text, font_name=self.font, font_size=self.font_size, x=self.center_x, y=self.center_y, anchor_x='center', anchor_y='center', color=self.text_color, batch=self.batch, group=foreground_group )
        self.button = pyglet.shapes.Rectangle( self.left, self.bottom, self.width, self.height, self.button_color[ : 3 ], batch=self.batch, group=self.background_group )
        self.button_hover = pyglet.shapes.Rectangle( self.left, self.bottom, self.width, self.height, self.button_hover_color[ : 3 ], batch=self.batch, group=self.background_group )
        self.button_click = pyglet.shapes.Rectangle( self.left, self.bottom, self.width, self.height, self.button_click_color[ : 3 ], batch=self.batch, group=self.background_group )
        self.button_hover.visible = False
        self.button_click.visible = False


    def check_hover( self, mouse_x, mouse_y ):
        if self.left < mouse_x < self.right and self.bottom < mouse_y < self.top:
            self.hover = True
            self.button_hover.visible = True
            self.button.visible = False
            return True
        else:
            self.hover = False
            self.button_hover.visible = False
            self.button.visible = True
            return False


    def check_click( self, mouse_x, mouse_y ):
        if self.check_hover( mouse_x, mouse_y ):
            self.click = True
            self.button_click.visible = True
            self.button_hover.visible = False
            self.button.visible = False
            return True

        else:
            return False


    def set_release( self ):
        self.click = False
        self.button_click.visible = False
        self.button.visible = True


    def on_screen_resize( self, width, height ):
        ## In this case, the width and height of the screen has changed.  So to check that a mouse is hovering over a button, we need to update self.left, self.right, self.bottom, and self.top since these no longer corresopnd to where the button actually renders on screen.
        ## Note, we don't have to change the vertex_lists or anything because we haven't changed resolution.  So the screen will still render properly, however mouse coordinates are affected, so we only have to update the internal button position for hover and click checks.
        self.window_width = width
        self.window_height = height
        self.center_x = self.center_x_ratio * self.window_width
        self.center_y = self.center_y_ratio * self.window_height
        self.width = self.width_ratio * self.window_width
        self.height = self.height_ratio * self.window_height
        self.left = self.center_x - self.width / 2
        self.right = self.center_x + self.width / 2
        self.bottom = self.center_y - self.height / 2
        self.top = self.center_y + self.height / 2


class Menu():

    def __init__( self, menu_title_text, game_window, font=None ):
        self.game_window = game_window
        self.font = font

        self.batch = pyglet.graphics.Batch()
        ## Background group is for buttons while foreground group is for button text.
        self.darken_group = pyglet.graphics.OrderedGroup( 0 )
        self.background_group = pyglet.graphics.OrderedGroup( 1 )
        self.foreground_group = pyglet.graphics.OrderedGroup( 2 )
        self.current_menu = False
        self.button_size_width = 1 / 4
        self.button_height = 2 / 3
        self.button_size_height = 1 / 9
        self.title_font_ratio = 72 / 720
        self.title_font_size = self.title_font_ratio * game_window.y_res
        self.font_ratio = 25 / 720
        self.slider_font_ratio = 25 / 720
        self.slider_font_size = self.slider_font_ratio * game_window.y_res
        self.slider_val_font_ratio = 18 / 720
        self.slider_val_font_size = self.slider_val_font_ratio * game_window.y_res
        self.font_size = self.font_ratio * game_window.y_res
        self.font_y = self.game_window.height * 6 / 7
        self.hovered_button = None
        self.clicked_button = None
        self.buttons = []
        ## Quad to darken whole screen
        self.menu_title_text = pyglet.text.Label( menu_title_text, font_name=self.font, font_size=self.title_font_size, x=self.game_window.width//2, y=self.font_y, anchor_x='center', anchor_y='center', batch=self.batch, group=self.background_group )


    def check_hover( self, mouse_x, mouse_y ):
        if self.hovered_button is not None:
            if not self.hovered_button.check_hover( mouse_x, mouse_y ):
                ## Then the mouse has been moved off the previously hovered button, and we set hovered_button to None.
                self.hovered_button = None
                ## Search through buttons to see if any other button is hovered over.
                for button in self.buttons:
                    if button.check_hover( mouse_x, mouse_y ):
                        self.hovered_button = button
                        break

        else:
            ## Search through buttons to see if any other button is hovered over.
            for button in self.buttons:
                if button.check_hover( mouse_x, mouse_y ):
                    self.hovered_button = button
                    break


    def check_click( self, x, y ):
        self.check_hover( x, y )
        if self.hovered_button is not None:
            if self.hovered_button.check_click( x, y ):
                self.clicked_button = self.hovered_button


    def check_release( self, x, y ):
        ## This function will be redefined in each particular subclass of Menu to perform the relevant actions.
        pass


    def draw( self ):
        ## Draw menu.  Draw menu_title_text and then draw buttons.
        self.batch.draw()


    def on_resize( self, width, height ):
        for button in self.buttons:
            button.on_screen_resize( width, height )


class IntroMenu( Menu ):
    def __init__( self, game_window, font=None ):
        self.font = font
        super().__init__( '', game_window, font=self.font )
        ## x-coordinate offset from middle of the screen for buttons
        self.offset = ( 1 / 7 ) * ( 3 / 4 ) + ( 1 / 8 ) * ( 1 / 4 )
        self.left_col_x = 1 / 2 - self.offset
        self.right_col_x = 1 / 2 + self.offset
        self.button_height = 1 / 6

        self.level_select_button = Button( self.game_window.width, self.game_window.height, center_x=self.left_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Level Select', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.options_button = Button( self.game_window.width, self.game_window.height, center_x=self.right_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Options', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.quit_button = Button( self.game_window.width, self.game_window.height, center_x=7/8, center_y=1/6, width=1/9, height=1/6, text='Quit\nGame', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group, multiline=True )
        self.buttons = [ self.level_select_button, self.options_button, self.quit_button ]


    def check_release( self, x, y ):
        if self.clicked_button is not None:
            if self.clicked_button.check_hover( x, y ):
                ## Then a button was clicked and released on, so we perform the relevant action.

                if self.clicked_button == self.level_select_button:
                    self.game_window.pause_menu.enter_submenu( self.game_window.pause_menu.level_select_menu )

                if self.clicked_button == self.options_button:
                    self.game_window.pause_menu.enter_submenu( self.game_window.pause_menu.options_menu )

                if self.clicked_button == self.quit_button:
                    self.game_window.on_close()

            self.clicked_button.set_release()
            self.clicked_button = None
            self.check_hover( x, y )




class MainPauseMenu( Menu ):
    def __init__( self, game_window, font=None ):
        self.font = font
        super().__init__( 'Paused', game_window, font=self.font )
        ## x-coordinate offset from middle of the screen for buttons
        self.offset = ( 1 / 7 ) * ( 3 / 4 ) + ( 1 / 8 ) * ( 1 / 4 )
        self.left_col_x = 1 / 2 - self.offset
        self.right_col_x = 1 / 2 + self.offset
        self.controls_text = 'W:Forward\nS:Backward\nA:Left\nD:Right\nLeft  Shift:Up\nSpacebar:Down\nEscape:Pause\nRight Click:Take A Screenshot\nMouse  Scroll: Change  Movement  Speed'
        self.controls_width = self.game_window.width * ( 2 / 3 )
        self.controls_text_left_x = ( self.left_col_x - self.button_size_width / 2 ) * self.game_window.width
        self.controls_text_y_offset = 1 / 20
        self.controls_text_top_y = ( self.button_height - self.button_size_height / 2 - self.controls_text_y_offset ) * self.game_window.height

        self.controls_image = pyglet.text.Label( self.controls_text, font_name=self.font, font_size=self.font_size, x=self.controls_text_left_x, y=self.controls_text_top_y, anchor_x='left', anchor_y='top', batch=self.batch, group=self.foreground_group, multiline=True, width=self.controls_width )
        self.level_select_button = Button( self.game_window.width, self.game_window.height, center_x=self.left_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Level Select', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.options_button = Button( self.game_window.width, self.game_window.height, center_x=self.right_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Options', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.quit_button = Button( self.game_window.width, self.game_window.height, center_x=7/8, center_y=1/6, width=1/9, height=1/6, text='Quit\nGame', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group, multiline=True )
        self.buttons = [ self.level_select_button, self.options_button, self.quit_button ]


    def check_release( self, x, y ):
        if self.clicked_button is not None:
            if self.clicked_button.check_hover( x, y ):
                ## Then a button was clicked and released on, so we perform the relevant action.

                if self.clicked_button == self.level_select_button:
                    self.game_window.pause_menu.enter_submenu( self.game_window.pause_menu.level_select_menu )

                if self.clicked_button == self.options_button:
                    self.game_window.pause_menu.enter_submenu( self.game_window.pause_menu.options_menu )

                if self.clicked_button == self.quit_button:
                    self.game_window.on_close()

            self.clicked_button.set_release()
            self.clicked_button = None
            self.check_hover( x, y )



class OptionsMenu( Menu ):
    def __init__( self, game_window, font=None ):
        self.font = font
        super().__init__( 'Options', game_window, font=self.font )
        self.button_row_2_y = 33 / 64
        ## x-coordinate offset from middle of the screen for buttons
        self.offset = ( 1 / 7 ) * ( 3 / 4 ) + ( 1 / 8 ) * ( 1 / 4 )
        self.left_col_x = 1 / 2 - self.offset
        self.right_col_x = 1 / 2 + self.offset
        self.slider_1_y = 23 / 64
        self.slider_2_y = 13 / 64

        ## Buttons
        self.wireframe_button = Button( self.game_window.width, self.game_window.height, center_x=self.left_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Toggle  Wireframe', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.textures_button = Button( self.game_window.width, self.game_window.height, center_x=self.right_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Toggle  Textures', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.skybox_button = Button( self.game_window.width, self.game_window.height, center_x=self.left_col_x, center_y=self.button_row_2_y, width=self.button_size_width, height=self.button_size_height, text='Toggle  Skybox', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.fps_button = Button( self.game_window.width, self.game_window.height, center_x=self.right_col_x, center_y=self.button_row_2_y, width=self.button_size_width, height=self.button_size_height, text='Toggle  FPS', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )

        ## Sliders
        self.fov_slider = Slider( 45, 30, 90, self.game_window.width, self.game_window.height, center_x = 1/2, center_y=self.slider_1_y, width=2/3, height=1/9, text="Field of View", text_font_size=self.slider_font_size, font=self.font, val_font_size=self.slider_val_font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.mouse_sensitivity_slider = Slider( 50, 1, 100, self.game_window.width, self.game_window.height, center_x = 1/2, center_y=self.slider_2_y, width=2/3, height=1/9, num_digits=0, text="Mouse Sensitivity", font=self.font, text_font_size=self.slider_font_size, val_font_size=self.slider_val_font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )

        ## Back button
        #self.back_button = Button( self.game_window.width, self.game_window.height, center_x=7/8, center_y=1/6, width=1/9, height=1/6, text='Back', font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.back_button = Button( self.game_window.width, self.game_window.height, center_x=1/8, center_y=6/7, width=1/9, height=1/6, text='Back', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )

        ## Button list ( also includes Sliders )
        self.buttons = [ self.wireframe_button, self.textures_button, self.skybox_button, self.fps_button, self.fov_slider, self.mouse_sensitivity_slider, self.back_button ]


    ## Redefine check_click from Menu class in order to deal with sliders.
    def check_click( self, x, y ):
        self.check_hover( x, y )
        if self.hovered_button is not None:
            if self.hovered_button.check_click( x, y ):
                self.clicked_button = self.hovered_button
                if self.clicked_button == self.fov_slider:
                    game_window.fov = ( self.fov_slider.current_val )
                    try:
                        game_window.skybox.skybox_set_fov( self.fov_slider.current_val )
                    except:
                        ## Then no skybox has been created yet.
                        pass
                if self.clicked_button == self.mouse_sensitivity_slider:
                    game_window.mouse_sensitivity = game_window.percent_to_sensitivity( self.mouse_sensitivity_slider.current_val )
                    game_window.set_mouse_sensitivity( game_window.mouse_sensitivity )


    def check_release( self, x, y ):
        if self.clicked_button is not None:
            if self.clicked_button.check_hover( x, y ):
                ## Then a button was clicked and released on, so we perform the relevant action.
                ## Toggle wireframe button.
                if self.clicked_button == self.wireframe_button:
                    if self.game_window.wireframe == False:
                        self.game_window.wireframe = True
                        glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )
                        glDisable( GL_DEPTH_TEST )
                        glDisable( GL_ALPHA_TEST )
                        glDisable( GL_BLEND )
                    else:
                        self.game_window.wireframe = False
                        glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
                        glEnable( GL_DEPTH_TEST )
                        glEnable( GL_ALPHA_TEST )
                        glEnable( GL_BLEND )

                ## Toggle textures button.
                if self.clicked_button == self.textures_button:
                    self.game_window.toggle_textures()

                ## Toggle skyboxes button.
                if self.clicked_button == self.skybox_button:
                    self.game_window.toggle_bool( 'load_skyboxes' )

                ## Toggle fps button.
                if self.clicked_button == self.fps_button:
                    self.game_window.toggle_bool( 'show_fps' )

                ## Back to the previous menu button.
                if self.clicked_button == self.back_button:
                        self.game_window.pause_menu.go_back()

            self.clicked_button.set_release()
            self.clicked_button = None
            self.check_hover( x, y )



    def check_drag( self, x, y, dx, dy, buttons, modifiers ):
        ## Check if either of the two slider objects are selected.
        if self.hovered_button == self.fov_slider or self.hovered_button == self.mouse_sensitivity_slider:
            ## If so, update the object so that it draws properly and stores the correct current_val.
            self.hovered_button.change_slider_pos( x )
            self.hovered_button.set_current_val()

            ## Update game_window and other objects with new values.
            if self.hovered_button == self.fov_slider:
                game_window.fov = self.fov_slider.current_val
                try:
                    game_window.skybox.skybox_set_fov( self.fov_slider.current_val )
                except:
                    ## Then no skybox has been created yet.
                    pass

            elif self.hovered_button == self.mouse_sensitivity_slider:
                game_window.mouse_sensitivity = game_window.percent_to_sensitivity( self.mouse_sensitivity_slider.current_val )
                game_window.set_mouse_sensitivity( game_window.mouse_sensitivity )




class LevelSelectMenu( Menu ):
    def __init__( self, game_window, page, font=None ):
        self.font = font
        super().__init__( 'Level Select', game_window, font=self.font )
        self.page = page
        self.back_button = Button( self.game_window.width, self.game_window.height, center_x=1/8, center_y=6/7, width=1/9, height=1/6, text='Back', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        if page == 1:
            self.next_button = Button( self.game_window.width, self.game_window.height, center_x=7/8, center_y=6/7, width=1/9, height=1/6, text='Next', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
            self.buttons = [ self.back_button, self.next_button ]
        else:
            self.buttons = [ self.back_button ]

        ## Level buttons will be in three columns.  self.edge_offset is the distance from the left edge of the screen to the left edge of the first button.  self.button_offset is the distance between the right edge of one button and the left edge of the next.  It is necessary that 3 * self.button_size_width + 2 * self.edge_offset + 2 * self.button_offset = 1.  Since the default self.button_size_width is 1/4, that means self.edge_offset + self.button_offset = 1/8.
        self.edge_offset = 3 / 32
        self.button_offset = ( ( 1 - ( 3 * self.button_size_width ) ) / 2 ) - self.edge_offset
        self.num_level_buttons = 15

        self.level_order = [ 'castle_grounds', 'castle_inside', 'castle_courtyard', 'bob', 'wf', 'jrb', 'ccm', 'bbh', 'hmc', 'lll', 'ssl', 'ddd', 'sl', 'wdw', 'ttm', 'thi', 'ttc', 'rr', 'pss', 'sa', 'wmotr', 'totwc', 'cotmc', 'vcutm', 'bitdw', 'bitfs', 'bits', 'bowser_1', 'bowser_2', 'bowser_3' ]

        self.display_names = { 'wdw': 'Wet Dry World', 'ttm': 'Tall Tall Mountain', 'thi': 'Tiny Huge Island', 'ddd': 'Dire Dire Docks', 'hmc': 'Hazy Maze Cave', 'bits': 'Bowser in the Sky', 'ccm': 'Cool Cool Mountain', 'pss': "Peach's Secret Slide", 'jrb': 'Jolly Roger Bay', 'rr': 'Rainbow Ride', 'bitfs': 'Bowser in the Fire Sea', 'cotmc': 'Cavern of the Metal Cap', 'bowser_1': 'Bowser 1 (Boss Area)', 'wmotr': 'Wing Mario Over the Rainbow', 'ttc': 'Tick Tock Clock', 'lll': 'Lethal Lava Land', 'totwc': 'Tower of the Wing Cap', 'wf': "Whomp's Fortress", 'ssl': 'Shifting Sand Land', 'sa': 'Secret Aquarium', 'vcutm': 'Vanish Cap Under The Moat', 'bob': 'Bob-Omb Battlefield', 'castle_courtyard': "Castle Courtyard", 'sl': "Snowman's Land", 'bitdw': 'Bowser in the Dark World', 'bbh': "Big Boo's Haunt", 'castle_inside': "Inside the Castle", 'bowser_3': 'Bowser 3 (Boss Area)', 'bowser_2': 'Bowser 2 (Boss Area)', 'castle_grounds': "Castle Grounds" }

        self.level_areas = { 'castle_grounds': 1, 'castle_inside': 3, 'castle_courtyard': 1, 'bob': 1, 'wf': 1, 'jrb': 2, 'ccm': 2, 'bbh': 1, 'hmc': 1, 'lll': 2, 'ssl': 3, 'ddd': 2, 'sl': 2, 'wdw': 2, 'ttm': 4, 'thi': 3, 'ttc': 1, 'rr': 1, 'pss': 1, 'sa': 1, 'wmotr': 1, 'totwc': 1, 'cotmc': 1, 'vcutm': 1, 'bitdw': 1, 'bitfs': 1, 'bits': 1, 'bowser_1': 1, 'bowser_2': 1, 'bowser_3': 1 }

        self.build_menu()


    def build_menu( self ):
        for i in range( self.num_level_buttons ):
            level_ind = ( self.page - 1 ) * self.num_level_buttons + i
            button_x = ( i % 3 ) * ( self.button_size_width + self.button_offset ) + ( ( self.button_size_width / 2 ) + self.edge_offset )
            button_y = ( 2 / 3 ) - ( i // 3 ) * ( 27 / 192 )
            button_name = self.level_order[ level_ind ] + '_button'
            display_text = self.display_names[ self.level_order[ level_ind ] ]
            setattr( self, button_name, Button( self.game_window.width, self.game_window.height, center_x=button_x, center_y=button_y, width=self.button_size_width, height=self.button_size_height, text=display_text, font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group ) )
            setattr( getattr( self, button_name ), 'level', self.level_order[ level_ind ] )
            setattr( getattr( self, button_name ), 'areas', self.level_areas [ self.level_order[ level_ind ] ] )
            self.buttons.append( getattr( self, button_name ) )


    def check_release( self, x, y ):
        if self.clicked_button is not None:
            if self.clicked_button.check_hover( x, y ):
                ## Then a button was clicked and released on, so we perform the relevant action.

                ## Back to the previous menu button.
                if self.clicked_button == self.back_button:
                    self.game_window.pause_menu.go_back()

                elif self.page == 1 and self.clicked_button == self.next_button:
                    self.game_window.pause_menu.enter_submenu( self.game_window.pause_menu.level_select_menu_2 )

                ## Buttons to load levels
                ## Only load levels with a single area for now.
                #elif hasattr( self.clicked_button, 'level' ) and self.clicked_button.areas == 1:
                elif hasattr( self.clicked_button, 'level' ):
                    self.game_window.load_new_level( self.clicked_button.level )

            self.clicked_button.set_release()
            self.clicked_button = None
            self.check_hover( x, y )



class PauseMenu():
    """The PauseMenu class mainly performs input handling and drawing while paused.  The actual menus will be instances of other classes that will subclass Menu."""

    def __init__( self, game_window, font=None ):
        self.game_window = game_window

        self.font = font

        self.pause_quad = pyglet.shapes.Rectangle( 0, 0, self.game_window.x_res, self.game_window.y_res, [ 0, 0, 0 ] )
        self.pause_quad.opacity = 160

        self.intro_menu = IntroMenu( self.game_window, font=self.font )
        self.main_pause_menu = MainPauseMenu( self.game_window, font=self.font )
        self.options_menu = OptionsMenu( self.game_window, font=self.font )
        self.level_select_menu = LevelSelectMenu( self.game_window, 1, font=self.font )
        self.level_select_menu_2 = LevelSelectMenu( self.game_window, 2, font=self.font )
        self.current_menu = self.intro_menu
        self.menus = [ self.intro_menu, self.main_pause_menu, self.options_menu, self.level_select_menu, self.level_select_menu_2 ]
        self.menu_stack = [ self.intro_menu ]


        self.event_dispatcher = pyglet.event.EventDispatcher()
        #self.event_dispatcher.register_event_type( 'on_pause' )


    def go_back( self ):
        self.menu_stack.pop()
        self.current_menu = self.menu_stack[ -1 ]


    def enter_submenu( self, menu ):
        self.current_menu = menu
        self.menu_stack.append( menu )


    def on_mouse_motion( self, x, y, dx, dy ):
        ## Forward action to the current menu.
        self.current_menu.check_hover( x, y )
        return True


    def on_mouse_press( self, x, y, button, modifiers ):
        ## Forward action to the current menu if left click.
        if button == pyglet.window.mouse.LEFT:
            self.current_menu.check_click( x, y )
            return True


    def on_mouse_release( self, x, y, button, modifiers ):
        ## Forward action to the current menu if left release.
        if button == pyglet.window.mouse.LEFT:
            self.current_menu.check_release( x, y )
        return True
        

    def on_mouse_drag( self, x, y, dx, dy, button, modifiers ):
        ## Forward action to the current menu if it is the Options menu.  That is the only menu that will have any elements that will deal with mouse drag.
        if button == pyglet.window.mouse.LEFT:
            if self.current_menu == self.options_menu:
                self.current_menu.check_drag( x, y, dx, dy, button, modifiers )
                return True


    def draw( self ):
        ## Set up Ortho matrix for 2D.
        glTexEnvi( GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE )
        glMatrixMode( GL_PROJECTION )
        glLoadIdentity()
        glOrtho( 0, self.game_window.x_res, 0, self.game_window.y_res, 0, 1 )

        ## Disable depth calculations.
        glDisable( GL_DEPTH_TEST )
        glDepthMask( GL_FALSE )

        ## If wireframe is enabled, we have to reenable polygon fill.
        if self.game_window.wireframe:
            glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
        glMatrixMode( GL_MODELVIEW )
        glLoadIdentity()

        ## Draw current pause menu.
        if self.current_menu != self.intro_menu:
            self.pause_quad.draw()
        self.current_menu.draw()

        ## If wireframe is enabled, disable polygon fill.
        if self.game_window.wireframe:
            glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )

        ## Re-enable depth calculations.
        glDepthMask( GL_TRUE )
        glEnable( GL_DEPTH_TEST )


    def on_screen_resize( self, width, height ):
        for each_menu in self.menus:
            each_menu.on_resize( width, height )



class GameWindow( pyglet.window.Window ):
    """Main game class.  Contains main game parameters as well as the level geometry, camera, level batch ( for the drawing of levels ), object batch ( for the drawing of objects ), and fps display."""
    def __init__( self, mario_graphics_dir, fullscreen=False, y_inv=False, vsync=False, resizable=True, load_textures=True, wireframe=False, load_skyboxes=True, original_res=False, show_fps=False, font=None ):
        self.mario_graphics_dir = mario_graphics_dir

        self.y_inv = y_inv
        self.fov = 45
        self.load_textures = load_textures
        self.font = font
        self.wireframe = wireframe
        self.paused = False
        self.full_res = fullscreen
        self.original_res = original_res
        self.load_skyboxes = load_skyboxes
        self.current_level = None
        self.mouse_sensitivity = 0.08
        self.min_mouse_sensitivity = 0.01
        self.max_mouse_sensitivity = 0.15143

        ## Implements MSAA.
        screen = pyglet.canvas.get_display().get_default_screen()
        template = pyglet.gl.Config( sample_buffers=1, samples=16 )
        try:
            config = screen.get_best_config( template )
        except:
            config = None

        ## Set screen resolution.
        self.max_x_res = pyglet.canvas.get_display().get_default_screen().width
        self.max_y_res = pyglet.canvas.get_display().get_default_screen().height
        self.set_resolution()

        super().__init__( self.x_res, self.y_res, "Mario 64", resizable=resizable, vsync=vsync, fullscreen=fullscreen, config=config )

        self.set_exclusive_mouse( False )

        self.set_opengl_state()

        self.level_geometry = Geometry( self.mario_graphics_dir )
        self.level_geometry.toggle_group_textures( self.load_textures )
        self.skybox_dict = { 'wdw':'wdw', 'ttm':'water', 'thi':'water', 'ddd':'water', 'hmc':None, 'bits':'bits', 'ccm':'ccm', 'pss':None, 'jrb':'clouds', 'rr':'cloud_floor', 'bitfs':'bitfs', 'cotmc':None, 'bowser_1':'bidw', 'wmotr':'cloud_floor', 'ttc':None, 'lll':'bitfs', 'totwc':'cloud_floor', 'wf':'cloud_floor', 'ssl':'ssl', 'sa':'cloud_floor', 'vcutm':None, 'bob':'water', 'castle_courtyard':'water', 'sl':'ccm', 'bitdw':'bidw', 'bbh':'bbh', 'castle_inside':None, 'bowser_3':'bits', 'bowser_2':'bitfs', 'castle_grounds':'water' }

        ## FPS Display
        self.show_fps = show_fps
        self.fps_display = pyglet.window.FPSDisplay( self )
        self.fps_display.update_period = 0.2

        ## Camera
        self.start_area = None
        self.start_yaw = None
        self.start_pos = None
        self.draw_distance = 100000
        self.camera = FirstPersonCamera( y_inv=self.y_inv )

        ## Create menus.
        self.pause_menu = PauseMenu( self, font=self.font )

        ## Load intro.
        self.in_intro = True
        self.level_batch = self.load_intro()
        self.push_handlers( self.pause_menu )

        pyglet.clock.schedule( self.on_update )


    def set_resolution( self ):
        if self.full_res:
            self.x_res = self.max_x_res
            self.y_res = self.max_y_res
        else:
            if self.original_res:
                self.x_res = 320
                self.y_res = 240
            else:
                self.x_res = 1280
                self.y_res = 720


    def set_opengl_state( self ):
        ## Set global OpenGL state based on GameWindow attributes.
        if self.wireframe:
            glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )
        else:
            glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
            glEnable( GL_DEPTH_TEST )
            material_reflectance = ( ctypes.c_float * 4 )( *( 1.0, 1.0, 1.0, 1.0 ) )
            light_direction = ( ctypes.c_float * 4 )( *( 1 / math.sqrt( 3 ), 1 / math.sqrt( 3 ), 1 / math.sqrt( 3 ), 0.0 ) )
            glLightfv( GL_LIGHT0, GL_POSITION, light_direction )
            glMaterialfv( GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, material_reflectance )
            glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST )
            glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR )


    def toggle_bool( self, attribute ):
        if getattr( self, attribute ) == False:
            setattr( self, attribute, True )
        else:
            setattr( self, attribute, False )


    def toggle_textures( self ):
        self.toggle_bool( 'load_textures' )
        self.level_geometry.toggle_group_textures( self.load_textures )


    def set_start_pos( self ):
        self.start_area, self.start_yaw, *self.start_pos = self.level_geometry.level_scripts[ self.current_level ].mario_pos
        for i in range( 3 ):
            self.start_pos[ i ] = -1 * self.start_pos[ i ]

        ## We'll load inside the floor if we don't add some height.  But because the camera has negative coordinates, we actually subtract 300 to add 300 height.
        self.start_pos[ 1 ] -= 300


    def load_intro( self ):
        self.current_level = 'intro'
        level_batch = self.level_geometry.load_intro()
        self.camera.position = [ 0, 130, -2300 ]
        self.camera.yaw = 0.0
        self.camera.pitch = 0.0
        self.skybox_present = False

        return level_batch


    def load_new_level( self, level, areas=True ):
        if self.in_intro:
            self.in_intro = False
            self.set_exclusive_mouse( True )
            self.pop_handlers()
            self.push_handlers( self.camera.input_handler )
        self.current_level = level
        self.set_start_pos()
        self.level_batch = self.level_geometry.load_level( level )
        ## Reset camera position to the new start_pos.
        self.camera.position = self.start_pos
        self.camera.yaw = self.start_yaw
        self.camera.pitch = 0.0
        if self.skybox_dict[ level ]:
            self.skybox = Skybox( self.skybox_dict[ level ], self.mario_graphics_dir )
            self.skybox.skybox_set_fov( self.fov )
            self.skybox_present = True
        else:
            self.skybox_present = False


    def on_mouse_press( self, x, y, button, modifiers ):
        if button == pyglet.window.mouse.RIGHT:
            time_str = time.strftime( "%Y_%m_%d_%H%M%S", time.localtime() ) + '.png'
            buf = ( GLubyte * ( 4 * self.width * self.height ) )( 0 )
            glReadPixels( 0, 0, self.width, self.height, GL_RGBA, GL_UNSIGNED_BYTE, buf )
            with open( str( ( screenshot_dir / time_str ).resolve() ), 'wb' ) as f:
                f.write( util_math.write_png( bytearray( buf ), self.width, self.height ) )
            return True


    def on_key_press( self, symbol, modifiers ):
        ## Pause/unpause the game.
        if symbol == pyglet.window.key.ESCAPE:
            if self.paused == True:
                self.paused = False
                self.set_exclusive_mouse( True )
                ## Stop PauseMenu from receiving user input and instead send the input to game_window.camera's input_handler.
                self.pop_handlers()
                self.push_handlers( self.camera.input_handler )
                self.pause_menu.current_menu = self.pause_menu.main_pause_menu
                self.pause_menu.menu_stack = [ self.pause_menu.main_pause_menu ]

            elif self.paused == False:
                if self.in_intro == True:
                    self.in_intro = False
                    self.set_exclusive_mouse( True )
                    self.pop_handlers()
                    self.push_handlers( self.camera.input_handler )

                else:
                    self.paused = True
                    self.set_exclusive_mouse( False )
                    self.set_mouse_position( int( self.width / 2 ), int( self.height / 2 ) )
                    self.pop_handlers()
                    self.pause_menu.current_menu = self.pause_menu.main_pause_menu
                    self.pause_menu.menu_stack = [ self.pause_menu.main_pause_menu ]
                    self.push_handlers( self.pause_menu )

            return True


    def sensitivity_to_percent( self, sensitivity ):
        """For user experience, the mouse sensitivity slider goes from 1 to 100.  However, the actual mouse sensitivity used will vary from self.min_mouse_sensitivity (corresponds to 1) to self.max_mouse_sensitivity (corresponds to 100).  This function takes an actual sensitivity value and converts it to a number between 1 and 100 inclusive."""
        return ( ( ( sensitivity - self.min_mouse_sensitivity ) / ( self.max_mouse_sensitivity - self.min_mouse_sensitivity ) ) * 99 + 1 )


    def percent_to_sensitivity( self, percent ):
        """For user experience, the mouse sensitivity slider goes from 1 to 100.  However, the actual mouse sensitivity used will vary from self.min_mouse_sensitivity (corresponds to 1) to self.max_mouse_sensitivity (corresponds to 100).  This function takes a number between 1 and 100 inclusive and converts it to the actual mouse sensitivity used."""
        return ( ( ( percent - 1 ) / 99 ) * ( self.max_mouse_sensitivity - self.min_mouse_sensitivity ) + self.min_mouse_sensitivity )


    def set_mouse_sensitivity( self, sensitivity ):
        self.camera.mouse_sensitivity = sensitivity


    def on_draw( self ):
        glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )

        ## Draw skybox first.
        if self.load_skyboxes:
            if self.skybox_present:
                self.skybox.update_and_draw( self.camera.yaw, self.camera.pitch )
    
        """
        Set the scene based on the camera's pitch, yaw, and position.
        Applies transforms.  We first rotate and then translate.
        Note that glRotatef( angle, x, y, z ) rotates by angle degrees around the vector ( x, y, z ).
        Since pitch is a rotation around the x-axis, we want to use ( 1, 0, 0 ).
        Since yaw is a rotation around the y-axis, we want to use ( 0, 1 , 0 ).
        Then we translate by the camera's position.  Note that the camera's position is already the negative of its actual worldview position.  Thus, we don't have to multiply by -1 when we're moving the world.
        Finally, we perform a 3D projection based on the fov and the resolution.
        """
        glMatrixMode( GL_MODELVIEW )
        glLoadIdentity()
        glRotatef( self.camera.pitch, 1.0, 0.0, 0.0 )
        glRotatef( self.camera.yaw, 0.0, 1.0, 0.0 )
        glTranslatef( *self.camera.position )
        #print( self.camera.pitch, self.camera.yaw, self.camera.position )
        glMatrixMode( GL_PROJECTION )
        glLoadIdentity()
        gluPerspective( self.fov, self.x_res / self.y_res, 10, self.draw_distance )
        glTexEnvi( GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE )

        ## Draw the actual level.
        self.level_batch.draw()

        if self.paused or self.in_intro:
            self.pause_menu.draw()
    
        if self.show_fps:
            if self.wireframe:
                glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
            self.fps_display.draw()
            if self.wireframe:
                glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )


    def on_update( self, dt ):
        if not self.paused:
            self.camera.update( dt )


    """
    def set_fov( self, fov ):
        print( 'here2' )
        self.fov = fov
        self.skybox.skybox_set_fov( self.fov )


    def on_pause( self ):
        print( 'here' )
    """


    def on_resize( self, width, height ):
        glViewport( 0, 0, width, height )
        if self.paused:
            self.pause_menu.on_screen_resize( width, height )


############
### MAIN ###
############
    
if __name__ == '__main__':

    mario_graphics_dir = Path( '/home/seph/game_practice/mario_64_graphics' )

    font_filename = 'super-mario-64.ttf'
    font_name = 'Super Mario 64'
    font_path = str( ( mario_graphics_dir / 'fonts' / font_filename ).resolve() )
    pyglet.font.add_file( font_path )

    screenshot_dir = mario_graphics_dir / 'screenshots'
    os.makedirs( screenshot_dir, exist_ok=True )

    game_window = GameWindow( mario_graphics_dir, fullscreen=False, y_inv=False, vsync=False, resizable=True, load_textures=True, wireframe=False, load_skyboxes=True, original_res=False, show_fps=False, font=font_name )

    ## Main game loop
    pyglet.app.run()

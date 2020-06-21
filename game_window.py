import pyglet
from pyglet.gl import *
import ctypes
import time
import os
import math

import util_math
from skybox import Skybox
from camera import FirstPersonCamera
from geometry import Geometry
from menus import Button, Slider, Menu, PauseMenu, IntroMenu, MainPauseMenu, OptionsMenu, LevelSelectMenu


class GameWindow( pyglet.window.Window ):
    """Main game class.  Contains main game parameters as well as the level geometry, camera, level batch (for the drawing of levels and objects), and fps display."""
    def __init__( self, mario_graphics_dir, fullscreen=False, resolution=None, y_inv=False, vsync=False, msaa=1, resizable=True, show_fps=False, font=None ):
        self.mario_graphics_dir = mario_graphics_dir
        self.screenshot_dir = mario_graphics_dir / 'screenshots'
        os.makedirs( self.screenshot_dir, exist_ok=True )

        self.y_inv = y_inv
        self.fov = 45
        self.font = font
        self.paused = False
        self.full_res = fullscreen
        self.resolution = resolution
        self.current_level = None
        self.mouse_sensitivity = 0.08
        self.min_mouse_sensitivity = 0.01
        self.max_mouse_sensitivity = 0.15143

        ## Graphics setings
        self.wireframe = False
        self.load_textures = True
        self.load_skyboxes = True

        ## MSAA.
        config = self.get_config( msaa )

        ## Set screen resolution and window border type.
        self.max_x_res = pyglet.canvas.get_display().get_default_screen().width
        self.max_y_res = pyglet.canvas.get_display().get_default_screen().height
        self.set_resolution()
        border_style = self.get_border_style( fullscreen )

        ## Init pyglet window.
        super().__init__( self.x_res, self.y_res, "Mario 64", resizable=resizable, vsync=vsync, fullscreen=False, config=config, style=border_style )

        if fullscreen:
            self.set_location( 0, 0 )

        ## Set mouse.
        self.exclusive_mouse = False
        self.set_exclusive_mouse( self.exclusive_mouse )

        ## Set OpenGL state.
        self.set_opengl_state()

        ## Geometry
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
        self.register_menu_event_types()
        self.pause_menu = PauseMenu( self.x_res, self.y_res, self.width, self.height, self.wireframe, font=self.font )
        self.set_menu_handlers()

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
            self.x_res, self.y_res = self.resolution
            if self.x_res > self.max_x_res:
                self.x_res = self.max_x_res
            if self.y_res > self.max_y_res:
                self.y_res = self.max_y_res


    def get_border_style( self, fullscreen ):
        if fullscreen:
            border_style = pyglet.window.Window.WINDOW_STYLE_BORDERLESS
        else:
            border_style = pyglet.window.Window.WINDOW_STYLE_DEFAULT

        return border_style


    def get_config( self, msaa ):
        if msaa > 1:
            screen = pyglet.canvas.get_display().get_default_screen()
            template = pyglet.gl.Config( sample_buffers=1, samples=msaa )
            try:
                config = screen.get_best_config( template )
            except:
                config = None

        else:
            config = None

        return config


    def set_opengl_state( self ):
        ## Set global OpenGL state based on GameWindow attributes.
        if self.wireframe:
            glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )
        else:
            glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
            glEnable( GL_DEPTH_TEST )
            glDepthMask( GL_TRUE )
            material_reflectance = ( ctypes.c_float * 4 )( *( 1.0, 1.0, 1.0, 1.0 ) )
            light_direction = ( ctypes.c_float * 4 )( *( 1 / math.sqrt( 3 ), 1 / math.sqrt( 3 ), 1 / math.sqrt( 3 ), 0.0 ) )
            glLightfv( GL_LIGHT0, GL_POSITION, light_direction )
            glMaterialfv( GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, material_reflectance )
            glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST )
            glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR )


    def set_start_pos( self ):
        self.start_area, self.start_yaw, *self.start_pos = self.level_geometry.level_scripts[ self.current_level ].mario_pos
        for i in range( 3 ):
            self.start_pos[ i ] = -1 * self.start_pos[ i ]

        ## We'll load partially inside the floor if we don't add some height.  But because the camera has negative coordinates, we actually subtract 300 to add 300 height.
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
            self.exclusive_mouse = True
            self.set_exclusive_mouse( self.exclusive_mouse )
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
            with open( str( ( self.screenshot_dir / time_str ).resolve() ), 'wb' ) as f:
                f.write( util_math.write_png( bytearray( buf ), self.width, self.height ) )
            return True


    def on_key_press( self, symbol, modifiers ):
        ## Pause/unpause the game.
        if symbol == pyglet.window.key.ESCAPE:
            self.pause_game()
            return True


    def on_resize( self, width, height ):
        glViewport( 0, 0, width, height )
        if hasattr( self, 'pause_menu' ):
            self.pause_menu.on_screen_resize( width, height )


    def on_activate( self ):
        self.set_exclusive_mouse( self.exclusive_mouse )


    def on_deactivate( self ):
        self.set_exclusive_mouse( False )


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

        ## Draw the menu, if applicable.
        if self.paused or self.in_intro:
            self.pause_menu.draw()
    
        ## Draw the FPS display, if applicable.
        if self.show_fps:
            if self.wireframe:
                glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
            self.fps_display.draw()
            if self.wireframe:
                glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )


    def on_update( self, dt ):
        if not self.paused:
            self.camera.update( dt )


    def register_menu_event_types( self ):
        ## Button Events
        Menu.register_event_type( 'exit_game' )
        Menu.register_event_type( 'go_back' )
        Menu.register_event_type( 'enter_submenu' )
        LevelSelectMenu.register_event_type( 'load_new_level' )
        OptionsMenu.register_event_type( 'toggle_skyboxes' )
        OptionsMenu.register_event_type( 'toggle_wireframe' )
        OptionsMenu.register_event_type( 'toggle_textures' )
        OptionsMenu.register_event_type( 'toggle_fps' )
        ## Slider Events
        OptionsMenu.register_event_type( 'set_fov' )
        OptionsMenu.register_event_type( 'set_mouse_sensitivity' )


    def set_menu_handlers( self ):
        ## OptionsMenu Buttons
        self.pause_menu.options_menu.set_handler( 'toggle_skyboxes', self.toggle_skyboxes )
        self.pause_menu.options_menu.set_handler( 'toggle_wireframe', self.toggle_wireframe )
        self.pause_menu.options_menu.set_handler( 'toggle_textures', self.toggle_textures )
        self.pause_menu.options_menu.set_handler( 'toggle_fps', self.toggle_fps )
        self.pause_menu.options_menu.set_handler( 'go_back', self.pause_menu.go_back )
        ## OptionsMenu Sliders
        self.pause_menu.options_menu.set_handler( 'set_fov', self.set_fov )
        self.pause_menu.options_menu.set_handler( 'set_mouse_sensitivity', self.set_mouse_sensitivity )

        ## IntroMenu
        self.pause_menu.intro_menu.set_handler( 'exit_game', self.exit_game )
        self.pause_menu.intro_menu.set_handler( 'enter_submenu', self.pause_menu.enter_submenu )

        ## MainPauseMenu
        self.pause_menu.main_pause_menu.set_handler( 'exit_game', self.exit_game )
        self.pause_menu.main_pause_menu.set_handler( 'enter_submenu', self.pause_menu.enter_submenu )

        ## LevelSelectMenu
        self.pause_menu.level_select_menu.set_handler( 'load_new_level', self.load_new_level )
        self.pause_menu.level_select_menu.set_handler( 'go_back', self.pause_menu.go_back )
        self.pause_menu.level_select_menu.set_handler( 'enter_submenu', self.pause_menu.enter_submenu )
        self.pause_menu.level_select_menu_2.set_handler( 'load_new_level', self.load_new_level )
        self.pause_menu.level_select_menu_2.set_handler( 'go_back', self.pause_menu.go_back )
        self.pause_menu.level_select_menu_2.set_handler( 'enter_submenu', self.pause_menu.enter_submenu )


    def pause_game( self ):
        if self.paused == True:
            self.paused = False
            self.exclusive_mouse = True
            self.set_exclusive_mouse( self.exclusive_mouse )
            ## Stop PauseMenu from receiving user input and instead send the input to the camera's input_handler.
            self.pop_handlers()
            self.push_handlers( self.camera.input_handler )
            self.pause_menu.current_menu = self.pause_menu.main_pause_menu
            self.pause_menu.menu_stack = [ self.pause_menu.main_pause_menu ]

        elif self.paused == False:
            if self.in_intro == True:
                self.in_intro = False
                self.exclusive_mouse = True
                self.set_exclusive_mouse( self.exclusive_mouse )
                self.pop_handlers()
                self.push_handlers( self.camera.input_handler )

            else:
                self.paused = True
                self.exclusive_mouse = False
                self.set_exclusive_mouse( self.exclusive_mouse )
                self.set_mouse_position( int( self.width / 2 ), int( self.height / 2 ) )
                self.pop_handlers()
                self.pause_menu.current_menu = self.pause_menu.main_pause_menu
                self.pause_menu.menu_stack = [ self.pause_menu.main_pause_menu ]
                self.push_handlers( self.pause_menu )


    def exit_game( self ):
        self.on_close()


    def toggle_bool( self, attribute ):
        if getattr( self, attribute ) == False:
            setattr( self, attribute, True )
        else:
            setattr( self, attribute, False )


    def toggle_textures( self ):
        self.toggle_bool( 'load_textures' )
        self.level_geometry.toggle_group_textures( self.load_textures )


    def toggle_wireframe( self ):
        if self.wireframe == False:
            self.wireframe = True
            glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )
            glDisable( GL_DEPTH_TEST )
            glDisable( GL_ALPHA_TEST )
            glDisable( GL_BLEND )
        else:
            self.wireframe = False
            glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
            glEnable( GL_DEPTH_TEST )
            glEnable( GL_ALPHA_TEST )
            glEnable( GL_BLEND )
        self.pause_menu.set_wireframe( self.wireframe )


    def toggle_fps( self ):
        self.toggle_bool( 'show_fps' )


    def toggle_skyboxes( self ):
        self.toggle_bool( 'load_skyboxes' )


    def set_fov( self, fov ):
        self.fov = fov
        if hasattr( self, 'skybox' ):
            self.skybox.skybox_set_fov( self.fov )


    def percent_to_sensitivity( self, percent ):
        """For user experience, the mouse sensitivity slider goes from 1 to 100.  However, the actual mouse sensitivity used will vary from self.min_mouse_sensitivity (corresponds to 1) to self.max_mouse_sensitivity (corresponds to 100).  This function takes a number between 1 and 100 inclusive and converts it to the actual mouse sensitivity used."""
        return ( ( ( percent - 1 ) / 99 ) * ( self.max_mouse_sensitivity - self.min_mouse_sensitivity ) + self.min_mouse_sensitivity )


    def set_mouse_sensitivity( self, sensitivity ):
        self.mouse_sensitivity = self.percent_to_sensitivity( sensitivity )
        self.camera.mouse_sensitivity = self.mouse_sensitivity



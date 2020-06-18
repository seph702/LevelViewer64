import pyglet
import math
import collections



class FirstPersonCamera():
    """Thanks, https://gist.github.com/mr-linch/f6dacd2a069887a47fbc!!"""

    DEFAULT_MOVEMENT_SPEED = 2000
    DEFAULT_MOUSE_SENSITIVITY = 0.08
    DEFAULT_KEY_MAP = {
            'forward': pyglet.window.key.W,
            'backward': pyglet.window.key.S,
            'left': pyglet.window.key.A,
            'right': pyglet.window.key.D,
            'up': pyglet.window.key.SPACE,
            'down': pyglet.window.key.LSHIFT,
            'pause': pyglet.window.key.ESCAPE
            }


    class InputHandler():
        def __init__( self ):
            self.pressed = collections.defaultdict( bool )
            self.pressed_once = collections.defaultdict( bool )
            self.dx = 0
            self.dy = 0
            self.scroll_y = 0
            self.mouse_x = 0
            self.mouse_y = 0
            self.mouse_left = False
            self.mouse_middle = False
            self.mouse_right = False
    
        def on_key_press( self, symbol, modifiers ):
            self.pressed[ symbol ] = True
    
            if self.pressed_once[ symbol ] == True:
                self.pressed_once[ symbol ] = False
            elif self.pressed_once[ symbol ] == False:
                self.pressed_once[ symbol ] = True
    
        def on_key_release( self, symbol, modifiers ):
            self.pressed[ symbol ] = False
    
        def on_mouse_motion( self, x, y, dx, dy ):
            self.dx = dx
            self.dy = dy
            self.mouse_x = x
            self.mouse_y = y
    
        def on_mouse_press( self, x, y, button, modifiers ):
            if button == pyglet.window.mouse.LEFT:
                self.mouse_left = True
            if button == pyglet.window.mouse.MIDDLE:
                self.mouse_middle = True
            if button == pyglet.window.mouse.RIGHT:
                self.mouse_right = True
    
        def on_mouse_release( self, x, y, button, modifiers ):
            if button == pyglet.window.mouse.LEFT:
                self.mouse_left = False
            if button == pyglet.window.mouse.MIDDLE:
                self.mouse_middle = False
            if button == pyglet.window.mouse.RIGHT:
                self.mouse_right = False
    
        def on_mouse_scroll( self, x, y, scroll_x, scroll_y ):
            self.scroll_y = scroll_y


    def __init__( self, position=[ 0.0, 0.0, 0.0 ], key_map=DEFAULT_KEY_MAP, movement_speed=DEFAULT_MOVEMENT_SPEED, mouse_sensitivity=DEFAULT_MOUSE_SENSITIVITY, y_inv=True ):
        """Creates camera.

        Args:
            position = initial 3d position of camera in model coords
            key_map = dict of ( actions, buttons ) = ( key, val )
            movement_speed = speed of camera movement
            mouse_sensitivity = speed of camera rotation
            y_inv = invert mouse y-axis
        """

        self.position = position
        self.yaw = 0.0
        self.pitch = 0.0

        self.input_handler = self.InputHandler()

        self.key_map = key_map
        self.movement_speed = movement_speed
        self.mouse_sensitivity = mouse_sensitivity
        self.min_mouse_sensitivity = 0.01
        self.max_mouse_sensitivity = 0.2
        self.y_inv = y_inv


    def set_mouse_sensitivity( self, sensitivity ):
        """Takes a float from 1 to 10 and maps it to the actual sensitivity used by the camera.

        Performs a linear transformation such that 1 maps to self.min_mouse_sensitivity and 10 maps to self.max_mouse_sensitivity."""
        self.mouse_sensitivity = self.min_mouse_sensitivity + ( ( sensitivity - 1 ) / ( 100 - 1 ) ) * ( self.max_mouse_sensitivity - self.min_mouse_sensitivity )


    def change_move_speed( self, mouse_wheel_clicks ):
        self.movement_speed *= 1.2 ** mouse_wheel_clicks


    def update_yaw( self, yaw ):
        """yaw is a representation of the rotation about the y-axis in degrees.  i.e. in the x-z plane.  Function updates internal yaw representation by yaw, taking mouse sensitivity into account."""
        self.yaw = ( self.yaw + ( yaw * self.mouse_sensitivity ) ) % 360

    def update_pitch( self, pitch ):
        """pitch is a representation of the rotation about the x-axis in degrees.  i.e. in the y-z plane.  Function updates internal pitch representation by pitch, taking mouse sensitivity into account."""
        if self.y_inv:
            self.pitch = ( self.pitch + ( pitch * self.mouse_sensitivity ) )
        else:
            self.pitch = ( self.pitch + ( pitch * self.mouse_sensitivity ) * ( -1 ) )

        if self.pitch < -89.0:
            self.pitch = -89.0
        elif self.pitch > 89.0:
            self.pitch = 89.0


    def move_forward( self, distance ):
        """Move the camera forward by the amount distance"""
        self.position[0] -= distance * math.sin( math.radians( self.yaw ) )
        self.position[2] += distance * math.cos( math.radians( self.yaw ) )

    def move_backward( self, distance ):
        """Move the camera backward by the amount distance"""
        self.position[0] += distance * math.sin( math.radians( self.yaw ) )
        self.position[2] -= distance * math.cos( math.radians( self.yaw ) )

    def move_left( self, distance ):
        """Move the camera left by the amount distance"""
        self.position[0] += distance * math.cos( math.radians( self.yaw ) )
        self.position[2] += distance * math.sin( math.radians( self.yaw ) )

    def move_right( self, distance ):
        """Move the camera right by the amount distance"""
        self.position[0] -= distance * math.cos( math.radians( self.yaw ) )
        self.position[2] -= distance * math.sin( math.radians( self.yaw ) )

    def move_up( self, distance ):
        """Move the camera up by the amount distance"""
        self.position[1] += distance

    def move_down( self, distance ):
        """Move the camera down by the amount distance"""
        self.position[1] -= distance



    def update( self, delta_time ):
        """Update camera state based on user input and time passed since the last update."""
        #print( time.perf_counter(), delta_time )

        ## Update movement_speed and reset input_handler
        self.change_move_speed( self.input_handler.scroll_y )
        self.input_handler.scroll_y = 0

        ## Update yaw and reset input_handler
        self.update_yaw( self.input_handler.dx )
        self.input_handler.dx = 0

        ## Update pitch and reset input_handler
        self.update_pitch( self.input_handler.dy )
        self.input_handler.dy = 0

        ## Detect key press using self.key_map and apply relevant actions
        if self.input_handler.pressed[ self.key_map[ 'forward' ] ]:
            self.move_forward( delta_time * self.movement_speed )

        if self.input_handler.pressed[ self.key_map[ 'backward' ] ]:
            self.move_backward( delta_time * self.movement_speed )

        if self.input_handler.pressed[ self.key_map[ 'left' ] ]:
            self.move_left( delta_time * self.movement_speed )

        if self.input_handler.pressed[ self.key_map[ 'right' ] ]:
            self.move_right( delta_time * self.movement_speed )

        if self.input_handler.pressed[ self.key_map[ 'up' ] ]:
            self.move_up( delta_time * self.movement_speed )

        if self.input_handler.pressed[ self.key_map[ 'down' ] ]:
            self.move_down( delta_time * self.movement_speed )

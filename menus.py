import pyglet
from pyglet.gl import *



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



class Menu( pyglet.event.EventDispatcher ):

    def __init__( self, menu_title_text, x_res, y_res, window_width, window_height, font=None ):
        self.x_res = x_res
        self.y_res = y_res
        self.window_width = window_width
        self.window_height = window_height
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
        self.title_font_size = self.title_font_ratio * self.y_res
        self.font_ratio = 25 / 720
        self.slider_font_ratio = 25 / 720
        self.slider_font_size = self.slider_font_ratio * self.y_res
        self.slider_val_font_ratio = 18 / 720
        self.slider_val_font_size = self.slider_val_font_ratio * self.y_res
        self.font_size = self.font_ratio * self.y_res
        self.font_y = self.window_height * 6 / 7
        self.hovered_button = None
        self.clicked_button = None
        self.buttons = []
        self.menu_title_text = pyglet.text.Label( menu_title_text, font_name=self.font, font_size=self.title_font_size, x=self.window_width//2, y=self.font_y, anchor_x='center', anchor_y='center', batch=self.batch, group=self.background_group )


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
        self.window_width = width
        self.window_height = height
        for button in self.buttons:
            button.on_screen_resize( width, height )



class IntroMenu( Menu ):
    def __init__( self, x_res, y_res, window_width, window_height, font=None ):
        super().__init__( '', x_res, y_res, window_width, window_height, font=font )
        ## x-coordinate offset from middle of the screen for buttons
        self.offset = ( 1 / 7 ) * ( 3 / 4 ) + ( 1 / 8 ) * ( 1 / 4 )
        self.left_col_x = 1 / 2 - self.offset
        self.right_col_x = 1 / 2 + self.offset
        self.button_height = 1 / 6

        self.level_select_button = Button( self.window_width, self.window_height, center_x=self.left_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Level Select', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.options_button = Button( self.window_width, self.window_height, center_x=self.right_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Options', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.quit_button = Button( self.window_width, self.window_height, center_x=7/8, center_y=1/6, width=1/9, height=1/6, text='Quit\nGame', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group, multiline=True )
        self.buttons = [ self.level_select_button, self.options_button, self.quit_button ]


    def check_release( self, x, y ):
        if self.clicked_button is not None:
            if self.clicked_button.check_hover( x, y ):
                ## Then a button was clicked and released on, so we perform the relevant action.

                if self.clicked_button == self.level_select_button:
                    self.dispatch_event( 'enter_submenu', 'level_select_menu' )

                if self.clicked_button == self.options_button:
                    self.dispatch_event( 'enter_submenu', 'options_menu' )

                if self.clicked_button == self.quit_button:
                    self.dispatch_event( 'exit_game' )

            self.clicked_button.set_release()
            self.clicked_button = None
            self.check_hover( x, y )



class MainPauseMenu( Menu ):
    def __init__( self, x_res, y_res, window_width, window_height, font=None ):
        super().__init__( 'Paused', x_res, y_res, window_width, window_height, font=font )
        ## x-coordinate offset from middle of the screen for buttons
        self.offset = ( 1 / 7 ) * ( 3 / 4 ) + ( 1 / 8 ) * ( 1 / 4 )
        self.left_col_x = 1 / 2 - self.offset
        self.right_col_x = 1 / 2 + self.offset
        self.controls_text = 'W:Forward\nS:Backward\nA:Left\nD:Right\nLeft  Shift:Up\nSpacebar:Down\nEscape:Pause\nRight Click:Take Screenshot\nMouse  Scroll: Change  Movement  Speed'
        self.controls_width = self.window_width * ( 2 / 3 )
        self.controls_text_left_x = ( self.left_col_x - self.button_size_width / 2 ) * self.window_width
        self.controls_text_y_offset = 1 / 50
        self.controls_text_top_y = ( self.button_height - self.button_size_height / 2 - self.controls_text_y_offset ) * self.window_height

        self.controls_image = pyglet.text.Label( self.controls_text, font_name=self.font, font_size=self.font_size, x=self.controls_text_left_x, y=self.controls_text_top_y, anchor_x='left', anchor_y='top', batch=self.batch, group=self.foreground_group, multiline=True, width=self.controls_width )
        self.level_select_button = Button( self.window_width, self.window_height, center_x=self.left_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Level Select', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.options_button = Button( self.window_width, self.window_height, center_x=self.right_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Options', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.quit_button = Button( self.window_width, self.window_height, center_x=7/8, center_y=1/6, width=1/9, height=1/6, text='Quit\nGame', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group, multiline=True )
        self.buttons = [ self.level_select_button, self.options_button, self.quit_button ]


    def check_release( self, x, y ):
        if self.clicked_button is not None:
            if self.clicked_button.check_hover( x, y ):
                ## Then a button was clicked and released on, so we perform the relevant action.

                if self.clicked_button == self.level_select_button:
                    self.dispatch_event( 'enter_submenu', 'level_select_menu' )

                if self.clicked_button == self.options_button:
                    self.dispatch_event( 'enter_submenu', 'options_menu' )

                if self.clicked_button == self.quit_button:
                    self.dispatch_event( 'exit_game' )

            self.clicked_button.set_release()
            self.clicked_button = None
            self.check_hover( x, y )



class OptionsMenu( Menu ):
    def __init__( self, x_res, y_res, window_width, window_height, font=None ):
        super().__init__( 'Options', x_res, y_res, window_width, window_height, font=font )
        self.button_row_2_y = 33 / 64
        ## x-coordinate offset from middle of the screen for buttons
        self.offset = ( 1 / 7 ) * ( 3 / 4 ) + ( 1 / 8 ) * ( 1 / 4 )
        self.left_col_x = 1 / 2 - self.offset
        self.right_col_x = 1 / 2 + self.offset
        self.slider_1_y = 23 / 64
        self.slider_2_y = 13 / 64

        ## Buttons
        self.wireframe_button = Button( self.window_width, self.window_height, center_x=self.left_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Toggle  Wireframe', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.textures_button = Button( self.window_width, self.window_height, center_x=self.right_col_x, center_y=self.button_height, width=self.button_size_width, height=self.button_size_height, text='Toggle  Textures', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.skybox_button = Button( self.window_width, self.window_height, center_x=self.left_col_x, center_y=self.button_row_2_y, width=self.button_size_width, height=self.button_size_height, text='Toggle  Skybox', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.fps_button = Button( self.window_width, self.window_height, center_x=self.right_col_x, center_y=self.button_row_2_y, width=self.button_size_width, height=self.button_size_height, text='Toggle  FPS', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )

        ## Sliders
        self.fov_slider = Slider( 45, 30, 90, self.window_width, self.window_height, center_x = 1/2, center_y=self.slider_1_y, width=2/3, height=1/9, text="Field of View", text_font_size=self.slider_font_size, font=self.font, val_font_size=self.slider_val_font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        self.mouse_sensitivity_slider = Slider( 50, 1, 100, self.window_width, self.window_height, center_x = 1/2, center_y=self.slider_2_y, width=2/3, height=1/9, num_digits=0, text="Mouse Sensitivity", font=self.font, text_font_size=self.slider_font_size, val_font_size=self.slider_val_font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )

        ## Back button
        self.back_button = Button( self.window_width, self.window_height, center_x=1/8, center_y=6/7, width=1/9, height=1/6, text='Back', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )

        ## Button list ( also includes Sliders )
        self.buttons = [ self.wireframe_button, self.textures_button, self.skybox_button, self.fps_button, self.fov_slider, self.mouse_sensitivity_slider, self.back_button ]


    ## Redefine check_click from Menu class in order to deal with sliders.
    def check_click( self, x, y ):
        self.check_hover( x, y )
        if self.hovered_button is not None:
            if self.hovered_button.check_click( x, y ):
                self.clicked_button = self.hovered_button
                if self.clicked_button == self.fov_slider:
                    self.dispatch_event( 'set_fov', self.fov_slider.current_val )

                if self.clicked_button == self.mouse_sensitivity_slider:
                    self.dispatch_event( 'set_mouse_sensitivity', self.mouse_sensitivity_slider.current_val )


    def check_release( self, x, y ):
        if self.clicked_button is not None:
            if self.clicked_button.check_hover( x, y ):
                ## Then a button was clicked and released on, so we perform the relevant action.
                ## Toggle wireframe button.
                if self.clicked_button == self.wireframe_button:
                    self.dispatch_event( 'toggle_wireframe' )

                ## Toggle textures button.
                if self.clicked_button == self.textures_button:
                    self.dispatch_event( 'toggle_textures' )

                ## Toggle skyboxes button.
                if self.clicked_button == self.skybox_button:
                    self.dispatch_event( 'toggle_skyboxes' )

                ## Toggle fps button.
                if self.clicked_button == self.fps_button:
                    self.dispatch_event( 'toggle_fps' )

                ## Back to the previous menu button.
                if self.clicked_button == self.back_button:
                    self.dispatch_event( 'go_back' )

            self.clicked_button.set_release()
            self.clicked_button = None
            self.check_hover( x, y )



    def check_drag( self, x, y, dx, dy, buttons, modifiers ):
        ## Check if either of the two slider objects are selected.
        if self.hovered_button == self.fov_slider or self.hovered_button == self.mouse_sensitivity_slider:
            ## If so, update the object so that it draws properly and stores the correct current_val.
            self.hovered_button.change_slider_pos( x )
            self.hovered_button.set_current_val()

            if self.hovered_button == self.fov_slider:
                self.dispatch_event( 'set_fov', self.fov_slider.current_val )

            elif self.hovered_button == self.mouse_sensitivity_slider:
                self.dispatch_event( 'set_mouse_sensitivity', self.mouse_sensitivity_slider.current_val )



class LevelSelectMenu( Menu ):
    def __init__( self, x_res, y_res, window_width, window_height, page, font=None ):
        super().__init__( 'Level Select', x_res, y_res, window_width, window_height, font=font )
        self.page = page
        self.back_button = Button( self.window_width, self.window_height, center_x=1/8, center_y=6/7, width=1/9, height=1/6, text='Back', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
        if page == 1:
            self.next_button = Button( self.window_width, self.window_height, center_x=7/8, center_y=6/7, width=1/9, height=1/6, text='Next', font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group )
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
            setattr( self, button_name, Button( self.window_width, self.window_height, center_x=button_x, center_y=button_y, width=self.button_size_width, height=self.button_size_height, text=display_text, font=self.font, font_size=self.font_size, batch=self.batch, foreground_group=self.foreground_group, background_group=self.background_group ) )
            setattr( getattr( self, button_name ), 'level', self.level_order[ level_ind ] )
            setattr( getattr( self, button_name ), 'areas', self.level_areas [ self.level_order[ level_ind ] ] )
            self.buttons.append( getattr( self, button_name ) )


    def check_release( self, x, y ):
        if self.clicked_button is not None:
            if self.clicked_button.check_hover( x, y ):
                ## Then a button was clicked and released on, so we perform the relevant action.

                ## Back to the previous menu button.
                if self.clicked_button == self.back_button:
                    self.dispatch_event( 'go_back' )

                elif self.page == 1 and self.clicked_button == self.next_button:
                    self.dispatch_event( 'enter_submenu', 'level_select_menu_2' )

                ## Buttons to load levels
                elif hasattr( self.clicked_button, 'level' ):
                    self.dispatch_event( 'load_new_level', self.clicked_button.level )

            self.clicked_button.set_release()
            self.clicked_button = None
            self.check_hover( x, y )



class PauseMenu():
    """The PauseMenu class mainly performs input handling and drawing while paused.  The actual menus will be instances of other classes that will subclass Menu."""

    def __init__( self, x_res, y_res, window_width, window_height, wireframe, font=None ):
        self.x_res = x_res
        self.y_res = y_res
        self.window_width = window_width
        self.window_height = window_height
        self.wireframe = wireframe

        self.font = font

        self.pause_quad = pyglet.shapes.Rectangle( 0, 0, self.x_res, self.y_res, [ 0, 0, 0 ] )
        self.pause_quad.opacity = 160

        self.intro_menu = IntroMenu( self.x_res, self.y_res, self.window_width, self.window_height, font=self.font )
        self.main_pause_menu = MainPauseMenu( self.x_res, self.y_res, self.window_width, self.window_height, font=self.font )
        self.options_menu = OptionsMenu( self.x_res, self.y_res, self.window_width, self.window_height, font=self.font )
        self.level_select_menu = LevelSelectMenu( self.x_res, self.y_res, self.window_width, self.window_height, 1, font=self.font )
        self.level_select_menu_2 = LevelSelectMenu( self.x_res, self.y_res, self.window_width, self.window_height, 2, font=self.font )
        self.current_menu = self.intro_menu
        self.menus = [ self.intro_menu, self.main_pause_menu, self.options_menu, self.level_select_menu, self.level_select_menu_2 ]
        self.menu_stack = [ self.intro_menu ]


    def go_back( self ):
        self.menu_stack.pop()
        self.current_menu = self.menu_stack[ -1 ]


    def enter_submenu( self, menu_name ):
        menu = getattr( self, menu_name )
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


    def set_wireframe( self, wireframe ):
        self.wireframe = wireframe


    def draw( self ):
        ## Set up Ortho matrix for 2D.
        glTexEnvi( GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE )
        glMatrixMode( GL_PROJECTION )
        glLoadIdentity()
        glOrtho( 0, self.x_res, 0, self.y_res, 0, 1 )

        ## Disable depth calculations.
        glDisable( GL_DEPTH_TEST )
        glDepthMask( GL_FALSE )

        ## If wireframe is enabled, we have to reenable polygon fill.
        if self.wireframe:
            glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )
        glMatrixMode( GL_MODELVIEW )
        glLoadIdentity()

        ## Draw current pause menu.
        if self.current_menu != self.intro_menu:
            self.pause_quad.draw()
        self.current_menu.draw()

        ## If wireframe is enabled, disable polygon fill.
        if self.wireframe:
            glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )

        ## Re-enable depth calculations.
        glDepthMask( GL_TRUE )
        glEnable( GL_DEPTH_TEST )


    def on_screen_resize( self, width, height ):
        for each_menu in self.menus:
            each_menu.on_resize( width, height )



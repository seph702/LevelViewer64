import pyglet
from pyglet.gl import *
from pathlib import Path



class Skybox():
    """The skybox is conceptually implemented by taking a single 256x256 image and drawing it twice on a 16x8 grid, where each tile corresponds to 32x32 pixels of the image.  The skybox "camera" then moves around this double image based on its pitch and yaw.

    The skybox calculation has been significantly changed and simplified from the original, official implementation so that the vertex_lists are fixed and only the glOrtho transform changes.  This means pyglet.graphics.vertex_list only has to be called the __init__.  This dramatically speeds up skybox rendering compared to the official implementation that changes the vertex lists every draw call.  Additionally, the skybox calculation has been generalized from the original to support arbitrary resolution and 1-359 degree field of view."""
    def __init__( self, image_name, image_dir ):


        self.short_name = image_name + '.png'
        self.sky_path = str( ( image_dir / 'skyboxes' / self.short_name ).resolve() )
        self.sky_image = pyglet.image.load( self.sky_path )
        self.skybox_texture = self.sky_image.get_texture()
        self.skybox_color_LUT = [ [ 0x50, 0x64, 0x5a ], [ 0xff, 0xff, 0xff ] ]
        self.skybox_colour_index = 1
        self.skybox_fov = 90
        self.skybox_cols = 8
        self.skybox_rows = 8
        self.skybox_width = self.skybox_cols
        self.skybox_height = self.skybox_rows
        self.skybox_tile_width = self.skybox_width / self.skybox_cols
        self.skybox_tile_height = self.skybox_height / self.skybox_rows
        self.x_skybox_tiles_onscreen = self.skybox_cols * ( self.skybox_fov / 360 )
        self.y_skybox_tiles_onscreen = self.skybox_rows * ( self.skybox_fov / 360 )
        self.skybox_batch = pyglet.graphics.Batch()
        self.build_batch()


    def skybox_set_fov( self, fov ):
        self.skybox_fov = 2 * fov
        self.skybox_width = self.skybox_cols
        self.skybox_height = self.skybox_rows
        self.skybox_tile_width = self.skybox_width / self.skybox_cols
        self.skybox_tile_height = self.skybox_height / self.skybox_rows
        self.x_skybox_tiles_onscreen = self.skybox_cols * ( self.skybox_fov / 360 )
        self.y_skybox_tiles_onscreen = self.skybox_rows * ( self.skybox_fov / 360 )

   
    def build_batch( self ):
        ## Texel coordinates. Because of the odd way Nintendo packed the images, we want 31 pixels out of the 32.  The 0.5 comes from converting from ST coordinates to UV coordinates.
        tc_0 = ( 0 + 0.5 ) / 32
        tc_1 = ( 31 + 0.5 ) / 32

        current_count = 4

        for row in range( self.skybox_rows ):
            for col in range( 2 * self.skybox_cols ):
                x = col
                y = self.skybox_height - row

                ## A single 256x256 texture is used.  We calculate which of the 64 subtextures to use and set the appropriate texel_coordinates.
                region_s0 = ( x / self.skybox_cols ) % 1
                region_t0 = ( y - 1 ) / self.skybox_rows
                s0 = tc_0 / self.skybox_cols + region_s0
                s1 = tc_1 / self.skybox_cols + region_s0
                t0 = tc_0 / self.skybox_rows + region_t0
                t1 = tc_1 / self.skybox_rows + region_t0
                current_texels = ( s0,t1, s0,t0, s1,t0, s1,t1 )

                current_vertices = ( x,y, x,y-self.skybox_tile_height, x+self.skybox_tile_width,y-self.skybox_tile_height, x+self.skybox_tile_width,y )

                self.skybox_batch.add_indexed( current_count, GL_TRIANGLES, None, ( 0, 1, 2, 0, 2, 3 ), ( 'v2f', current_vertices ), ( 't2f', current_texels ) )
                


    def update_and_draw( self, yaw, pitch ):
        ## Calculate scaled x.
        x_scaled = ( yaw / 360 ) * self.skybox_width

        ## Calculate scaled y.
        pitch_scaled = ( pitch + 90 ) / 180
        y_scaled = ( self.skybox_rows - self.y_skybox_tiles_onscreen ) * pitch_scaled

        ## Prepare OpenGL to draw background by setting up an Ortho matrix.
        glTexEnvi( GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE )
        glMatrixMode( GL_PROJECTION )
        glLoadIdentity()
        left = x_scaled
        right = x_scaled + self.x_skybox_tiles_onscreen * self.skybox_tile_width
        bottom = self.skybox_height - y_scaled - self.y_skybox_tiles_onscreen
        top = self.skybox_height - y_scaled
        glOrtho( left, right, bottom, top, 0, 3 )

        ## Disable depth testing.
        glDisable( GL_DEPTH_TEST )
        glDepthMask( GL_FALSE )
        glMatrixMode( GL_MODELVIEW )
        glLoadIdentity()

        ## Bind texture to prepare for draw.
        glEnable( GL_TEXTURE_2D )
        glBindTexture( GL_TEXTURE_2D, self.skybox_texture.id )

        self.skybox_batch.draw()

        ## Disable texture.
        glDisable( GL_TEXTURE_2D )

        ## Reenable depth testing.
        glDepthMask( GL_TRUE )
        glEnable( GL_DEPTH_TEST )

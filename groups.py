import math
import ctypes
import pyglet
from pyglet.gl import *

import util_math


class TextureEnableGroup( pyglet.graphics.Group ):
    def __init__( self, parent ):
        self.load_textures = True
        super( TextureEnableGroup, self ).__init__( parent )

    def set_state( self ):
        if self.load_textures:
            glEnable( GL_TEXTURE_2D )
        else:
            glDisable( GL_TEXTURE_2D )

    def unset_state( self ):
        glDisable( GL_TEXTURE_2D )

    def toggle_textures( self, texture_bool ):
        self.load_textures = texture_bool


class TextureBindGroup( pyglet.graphics.Group ):
    ## The parent should be set to a TextureEnableGroup under the appropriate LayerNGroup.
    def __init__( self, texture, parent ):
        super( TextureBindGroup, self ).__init__( parent )
        assert texture.target == GL_TEXTURE_2D
        self.texture = texture

    def set_state( self ):
        glBindTexture( GL_TEXTURE_2D, self.texture.id )

    # No unset_state method required.

    def __eq__( self, other ):
        return ( self.__class__ is other.__class__ and
                self.texture.id == other.texture.id and
                self.texture.target == other.texture.target and
                self.parent == other.parent )

    def __hash__( self ):
        return hash( ( self.texture.id, self.texture.target ) )


class Layer0Group( pyglet.graphics.OrderedGroup ):
    ## Layer FORCE
    def __init__( self ):
        super( Layer0Group, self ).__init__( 0 )

    def set_state( self ):
        glEnable( GL_DEPTH_TEST )
        pass

    def unset_state( self ):
        pass


class Layer1Group( pyglet.graphics.OrderedGroup ):
    ## Layer OPAQUE
    def __init__( self ):
        super( Layer1Group, self ).__init__( 1 )

    def set_state( self ):
        glEnable( GL_DEPTH_TEST )
        glDepthMask( GL_TRUE )

    def unset_state( self ):
        pass


class Layer2Group( pyglet.graphics.OrderedGroup ):
    ## Layer OPAQUE_DECAL
    def __init__( self ):
        super( Layer2Group, self ).__init__( 2 )

    def set_state( self ):
        glEnable( GL_DEPTH_TEST )
        glDepthMask( GL_FALSE )
        glPolygonOffset( -2, -2 )
        glEnable( GL_POLYGON_OFFSET_FILL )

    def unset_state( self ):
        glDepthMask( GL_TRUE )
        glPolygonOffset( 0, 0 )
        glDisable( GL_POLYGON_OFFSET_FILL )


class Layer3Group( pyglet.graphics.OrderedGroup ):
    ## Layer OPAQUE INTER
    def __init__( self ):
        super( Layer3Group, self ).__init__( 3 )

    def set_state( self ):
        glDepthMask( GL_TRUE )

    def unset_state( self ):
        pass


class Layer4Group( pyglet.graphics.OrderedGroup ):
    ## Layer ALPHA
    def __init__( self ):
        super( Layer4Group, self ).__init__( 4 )

    def set_state( self ):
        #glEnable( GL_BLEND )
        glEnable( GL_ALPHA_TEST )
        glAlphaFunc( GL_GREATER, 0.49 )

    def unset_state( self ):
        glDisable( GL_ALPHA_TEST )


class Layer5Group( pyglet.graphics.OrderedGroup ):
    ## Layer TRANSPARENT
    def __init__( self ):
        super( Layer5Group, self ).__init__( 5 )

    def set_state( self ):
        glEnable( GL_BLEND )
        glDepthMask( GL_FALSE )

    def unset_state( self ):
        glDepthMask( GL_TRUE )


class Layer6Group( pyglet.graphics.OrderedGroup ):
    ## Layer TRANSPARENT_DECAL
    def __init__( self ):
        super( Layer6Group, self ).__init__( 6 )

    def set_state( self ):
        glEnable( GL_BLEND )
        glDepthMask( GL_FALSE )
        glPolygonOffset( -2, -2 )
        glEnable( GL_POLYGON_OFFSET_FILL )

    def unset_state( self ):
        glPolygonOffset( 0, 0 )
        glDepthMask( GL_TRUE )
        glDisable( GL_POLYGON_OFFSET_FILL )


class Layer7Group( pyglet.graphics.OrderedGroup ):
    ## Layer TRANSPARENT_INTER
    def __init__( self ):
        super( Layer7Group, self ).__init__( 7 )

    def set_state( self ):
        glEnable( GL_BLEND )
        glDepthMask( GL_FALSE )
        glPolygonOffset( -2, -2 )
        glEnable( GL_POLYGON_OFFSET_FILL )

    def unset_state( self ):
        glPolygonOffset( 0, 0 )
        glDisable( GL_POLYGON_OFFSET_FILL )
        glDisable( GL_BLEND )
        glDepthMask( GL_TRUE )
        glDisable( GL_DEPTH_TEST )


class RenderSettingsGroup( pyglet.graphics.Group ):
    def __init__( self, parent, geometry_mode, current_lights, combine_mode, env_colour ):
        super( RenderSettingsGroup, self ).__init__( parent )
        self.enable_lighting = False
        self.texture_gen = False
        self.tex_gen_arr = None
        self.ambient = ( 0, 0, 0, 1 )
        self.diffuse_direction = ( 0, 0, 0, 0 )
        self.diffuse_colors = ( 0, 0, 0, 1 )
        self.combine_mode = None
        self.env_tuple = ( 0.0, 0.0, 0.0, 0.0 )
        self.env_colour = None
        self.parse_render_info( geometry_mode, combine_mode, current_lights, env_colour )
        self.set_state_setter()


    def parse_render_info( self, geometry_mode, combine_mode, current_lights, env_colour ):
        ## Parse texture gen
        self.texture_gen = geometry_mode.get( 'G_TEXTURE_GEN' )
        if self.texture_gen is not None:
            self.tex_gen_arr = ( ctypes.c_int * 1 )( GL_SPHERE_MAP )

        ## Parse lighting
        self.enable_lighting = geometry_mode[ 'G_LIGHTING' ]
        if self.enable_lighting:
            keys = list( current_lights )
            for each_key in keys:
                if len( current_lights[ each_key ] ) == 3:
                    ambient_list = [ *[ i / 255.0 for i in current_lights[ each_key ] ], 1.0 ]
                    self.ambient = ( ctypes.c_float * len( ambient_list ) )( *ambient_list )
                else:
                    diffuse_color_list = [ *[ i / 255.0 for i in current_lights[ each_key ][ : 3 ] ], 1.0 ]
                    if env_colour is not None:
                        diffuse_color_list[ 3 ] = env_colour[ 3 ] / 255.0
                    diffuse_direction_list_unnormalized = util_math.convert_twos_comp_list( current_lights[ each_key ][ 3 : ] ) + [ 0.0 ]

                    normalization_factor = 1 / math.sqrt( sum ( [ i**2 for i in diffuse_direction_list_unnormalized ] ) )
                    diffuse_direction_list = [ normalization_factor * i for i in diffuse_direction_list_unnormalized ] + [ 0.0 ]
                    self.diffuse_colors = ( ctypes.c_float * len( diffuse_color_list ) )( *diffuse_color_list )

        ## Parse combine mode
        try:
            combine_str = combine_mode[ 0 ][ len( 'G_CC_' ) : ]
            if combine_str[ : 8 ] == 'MODULATE':
                self.combine_mode = GL_MODULATE
            elif combine_str[ : 5 ] == 'DECAL':
                self.combine_mode = GL_MODULATE
            elif combine_str[ : 5 ] == 'BLEND':
                self.combine_mode = GL_MODULATE
            else:
                self.combine_mode = GL_MODULATE
        except:
            self.combine_mode = GL_MODULATE

        ## Parse environment colour
        if env_colour is not None:
            self.env_tuple = tuple( i / 255.0 for i in env_colour )
            self.env_colour = ( ctypes.c_float * 4 )( *self.env_tuple )
            self.reset_env_colour = ( ctypes.c_float * 4 )( *( 0.0, 0.0, 0.0, 0.0 ) )
            self.reset_mat_colour = ( ctypes.c_float * 4 )( *( 1.0, 1.0, 1.0, 1.0 ) )


    def no_lighting_set_state( self ):
        pass

    def no_lighting_unset_state( self ):
        pass

    def tex_gen_lighting_no_transparency_set_state( self ):
        glTexGeniv( GL_S, GL_TEXTURE_GEN_MODE, self.tex_gen_arr )
        glEnable( GL_TEXTURE_GEN_S )
        glEnable( GL_LIGHTING )
        glLightfv( GL_LIGHT0, GL_AMBIENT, self.ambient )
        glLightfv( GL_LIGHT0, GL_DIFFUSE, self.diffuse_colors )
        glEnable( GL_LIGHT0 )

    def tex_gen_lighting_no_transparency_unset_state( self ):
        glDisable( GL_TEXTURE_GEN_S )
        glDisable( GL_LIGHT0 )
        glDisable( GL_LIGHTING )

    def lighting_no_transparency_set_state( self ):
        glEnable( GL_LIGHTING )
        glLightfv( GL_LIGHT0, GL_AMBIENT, self.ambient )
        glLightfv( GL_LIGHT0, GL_DIFFUSE, self.diffuse_colors )
        glEnable( GL_LIGHT0 )

    def lighting_no_transparency_unset_state( self ):
        glDisable( GL_LIGHT0 )
        glDisable( GL_LIGHTING )

    def lighting_transparency_set_state( self ):
        glEnable( GL_LIGHTING )
        glLightfv( GL_LIGHT0, GL_AMBIENT, self.ambient )
        glLightfv( GL_LIGHT0, GL_DIFFUSE, self.diffuse_colors )
        glEnable( GL_LIGHT0 )
        glMaterialfv( GL_FRONT, GL_AMBIENT_AND_DIFFUSE, self.env_colour )

    def lighting_transparency_unset_state( self ):
        glDisable( GL_LIGHT0 )
        glDisable( GL_LIGHTING )
        glMaterialfv( GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, self.reset_mat_colour )


    def set_state_setter( self ):
        if not self.enable_lighting:
            self.set_state = self.no_lighting_set_state
            self.unset_state = self.no_lighting_unset_state

        else:
            if self.texture_gen:
                self.set_state = self.tex_gen_lighting_no_transparency_set_state
                self.unset_state = self.tex_gen_lighting_no_transparency_unset_state

            else:
                if self.env_tuple != ( 0.0, 0.0, 0.0, 0.0 ):
                    self.set_state = self.lighting_transparency_set_state
                    self.unset_state = self.lighting_transparency_unset_state

                else:
                    ## No transparency.
                    self.set_state = self.lighting_no_transparency_set_state
                    self.unset_state = self.lighting_no_transparency_unset_state


    def __eq__( self, other ):
        return ( self.__class__ is other.__class__ and
                self.parent == other.parent and
                self.enable_lighting == other.enable_lighting and
                self.combine_mode == other.combine_mode and
                self.env_tuple == other.env_tuple and
                tuple( self.ambient ) == tuple( other.ambient ) and
                tuple( self.diffuse_direction ) == tuple( other.diffuse_direction ) and
                tuple( self.diffuse_colors ) == tuple( other.diffuse_colors ) )
                
    def __hash__( self ):
        return hash( ( self.parent, self.enable_lighting, self.combine_mode, self.env_tuple, tuple( self.ambient ), tuple( self.diffuse_direction ), tuple( self.diffuse_colors ) ) )

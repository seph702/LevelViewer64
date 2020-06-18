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
#from geometry import Geometry


###############
### CLASSES ###
###############


class Geometry():
    def __init__( self ):
        self.layer_dict = { 'LAYER_FORCE' : 0, 'LAYER_OPAQUE' : 1, 'LAYER_OPAQUE_DECAL' : 2, 'LAYER_OPAQUE_INTER' : 3, 'LAYER_ALPHA' : 4, 'LAYER_TRANSPARENT' : 5, 'LAYER_TRANSPARENT_DECAL' : 6, 'LAYER_TRANSPARENT_INTER' : 7 }
        self.reverse_layer_dict = { 0: 'LAYER_FORCE', 1: 'LAYER_OPAQUE', 2: 'LAYER_OPAQUE_DECAL', 3: 'LAYER_OPAQUE_INTER', 4: 'LAYER_ALPHA', 5: 'LAYER_TRANSPARENT', 6: 'LAYER_TRANSPARENT_DECAL', 7: 'LAYER_TRANSPARENT_INTER' }
        self.batch = None
        self.texture_atlas = None
        ## We don't want to create new texture groups for the same texture, so we'll make a texture_group_dict which has keys texture_filename and values TextureBindGroup
        self.texture_group_dict = {}
        self.texture_atlas_dict = {}
        self.build_groups()


    def build_groups( self ):
        ## Creates the two top levels of the group structure: the layer ( draw order ) groups and texture enable groups.
        self.layer0group = Layer0Group()
        self.layer1group = Layer1Group()
        self.layer2group = Layer2Group()
        self.layer3group = Layer3Group()
        self.layer4group = Layer4Group()
        self.layer5group = Layer5Group()
        self.layer6group = Layer6Group()
        self.layer7group = Layer7Group()
        for i in range( 8 ):
            setattr( self, 'texture_enable_group_' + str( i ), TextureEnableGroup( getattr( self, 'layer' + str( i ) + 'group' ) ) )
        self.texture_enable_groups = [ self.texture_enable_group_0, self.texture_enable_group_1, self.texture_enable_group_2, self.texture_enable_group_3, self.texture_enable_group_4, self.texture_enable_group_5, self.texture_enable_group_6, self.texture_enable_group_7 ]


    def toggle_group_textures( self, texture_bool ):
        for each_group in self.texture_enable_groups:
            each_group.toggle_textures( texture_bool )


    def load_intro( self ):
        ## Reset batch and texture_group_dict.
        self.texture_atlas = pyglet.image.atlas.TextureAtlas()
        self.texture_atlas_dict = {}
        self.batch = pyglet.graphics.Batch()
        self.texture_group_dict = {}
        logo_dl = 'intro_seg7_dl_0700B3A0'
        copyright_dl = 'intro_seg7_dl_0700C6A0'

        ## Add logo to batch.
        for each_gfx_draw_list in gfx_display_dict[ logo_dl ]:
            current_layer = 'LAYER_OPAQUE'
            current_transformation = util_math.identity_mat()
            self.add_drawlist_to_batch( each_gfx_draw_list, current_layer, current_transformation )

        ## Add copyright to batch.
        for each_gfx_draw_list in gfx_display_dict[ copyright_dl ]:
            if each_gfx_draw_list.name == 'intro_seg7_vertex_0700B420':
                current_layer = 'LAYER_OPAQUE'
                current_transformation = util_math.identity_mat()
                self.add_drawlist_to_batch( each_gfx_draw_list, current_layer, current_transformation )

        return self.batch


    def load_object( self, obj, level_to_load, current_area_offset ):
        if 'LEVEL_GEOMETRY' in obj.model or 'special_level_geo' in obj.model:
            if obj.type == 'SPECIAL_OBJECT':
                try:
                    geo_name = level_to_load.level_geo[ special_dict[ obj.model ] ]
                    geo_to_load = level_to_load.geo_dict[ geo_name ]
                except:
                    geo_name = obj_name_to_geo_dict[ obj.model ]
                    geo_to_load = geo_dict[ geo_name ]
            else:
                geo_name = level_to_load.level_geo[ obj.model ]
                geo_to_load = level_to_load.geo_dict[ geo_name ]
            self.process_geo_to_batch( geo_to_load, current_area_offset, obj_position=obj.position, obj_rotation=obj.angle )
        else:
            try:
                geo_name = obj_name_to_geo_dict[ obj.model ]
                extra_scale = get_extra_scale( obj.model, obj.beh, obj.behParam, geo_name ) or 1.0
                geo_to_load = geo_dict[ geo_name ]
                self.process_geo_to_batch( geo_to_load, current_area_offset, obj_position=obj.position, obj_rotation=obj.angle, obj_scale=extra_scale )
            except Exception as e:
                pass
                #print( e )


    def load_level( self, level ):
        ## Reset batch, atlas, texture_atlas_dict, and texture_group_dict.
        self.batch = pyglet.graphics.Batch()
        self.texture_atlas = pyglet.image.atlas.TextureAtlas()
        ## texture_atlas_dict will keep track of TextureRegions in the atlas.
        self.texture_atlas_dict = {}
        self.texture_group_dict = {}

        level_to_load = level_scripts[ level ]
        for area in level_to_load.areas:
            current_area_offset = area.offset

            ## First load strictly area geo.  Note that this excludes objects and special objects that may be part of the level geometry.
            for geo_to_load in area.geo:
                root_area_geo = level_to_load.geo_dict[ geo_to_load ]
                self.process_geo_to_batch( root_area_geo, current_area_offset )

            ## Next, load any objects with acts.
            for each_obj in area.objs_with_acts:
                self.load_object( each_obj, level_to_load, current_area_offset )

            ## Next, load any objects.
            for each_obj in area.objs:
                self.load_object( each_obj, level_to_load, current_area_offset )

            ## Next, load any special objects.
            for each_special_obj in area.special_objs:
                self.load_object( each_special_obj, level_to_load, current_area_offset )

            ## Next, load any macro objects.
            for each_macro_obj in area.macro_objs:
                self.load_object( each_macro_obj, level_to_load, current_area_offset )

            ## Next, load any movtex objects.
            for each_movtex_obj in area.movtex:
                if isinstance( each_movtex_obj, WaterBox ):
                    ## If the movtex object is a waterbox, load waterbox.
                    self.add_waterbox_to_batch( each_movtex_obj, current_area_offset )

                elif isinstance( each_movtex_obj, Movtex_Tri ):
                    ## If the movtex object is a movtex tri, load it.
                    self.add_movtex_tri_to_batch( each_movtex_obj, current_area_offset )

            ## Load any paintings.
            for each_painting in area.paintings:
                self.add_painting_to_batch( each_painting, current_area_offset )


        return self.batch



    def process_geo_to_batch( self, geo, area_offset, obj_position=[ 0, 0, 0 ], obj_rotation=[ 0, 0, 0 ], obj_scale=1.0 ):
        #shadows = geo.shadows
        geo_dls = geo.geo_dls

        for each_geo_dl in geo_dls:

            current_layer = each_geo_dl.layer
            if type( current_layer ) is int:
                current_layer = self.reverse_layer_dict[ current_layer ]

            current_translation = [ 0, 0, 0 ]
            ## Update translation by area offset and obj_position.:
            for i in range( 3 ):
                current_translation[ i ] += area_offset[ i ] + obj_position[ i ]
            translate_mat = util_math.translate_mat( current_translation[ 0 ], current_translation[ 1 ], current_translation[ 2 ] )
            
            transform = each_geo_dl.transformation
            obj_scale_mat = util_math.scale_mat( obj_scale )
            obj_rot_x = util_math.rotate_around_x( obj_rotation[ 0 ] )
            obj_rot_y = util_math.rotate_around_y( obj_rotation[ 1 ] )
            obj_rot_z = util_math.rotate_around_z( obj_rotation[ 2 ] )

            transformation_mat = transform @ obj_scale_mat @ obj_rot_y @ obj_rot_x @ obj_rot_z @ translate_mat

            for each_gfx_draw_list in gfx_display_dict[ each_geo_dl.dl_name ]:
                ## Values in gfx_draw_dict are GfxDrawLists, which have attributes render_settings, positions, triangles, texel_coordinates, and colors.
                if each_geo_dl.billboard and current_layer != 'LAYER_ALPHA' and each_gfx_draw_list.render_settings.geometry_mode[ 'G_LIGHTING' ] == True:
                    print( each_geo_dl.dl_name, each_geo_dl.layer, each_gfx_draw_list.render_settings.geometry_mode )
                self.add_drawlist_to_batch( each_gfx_draw_list, current_layer, transformation_mat )


    def add_drawlist_to_batch( self, gfx_draw_list, current_layer, transformation_matrix ):

        current_group = getattr( self, 'layer' + str( self.layer_dict[ current_layer ] ) + 'group' )
        current_texture_enable = gfx_draw_list.render_settings.texture_enable and gfx_draw_list.render_settings.current_texture

        current_texels = [ util_math.s10_5_to_int( i ) + 0.5  for i in gfx_draw_list.texel_coordinates ]

        if current_texture_enable:

            if texture_dict.get( gfx_draw_list.render_settings.current_texture ) is not None:
                texture_filename = texture_dict[ gfx_draw_list.render_settings.current_texture ]
                if self.texture_group_dict.get( texture_filename ):
                    current_texture_info = self.texture_group_dict[ texture_filename ]
                    current_texture = current_texture_info[ 0 ]

                    s_scale = current_texture_info[ 1 ]
                    t_scale = current_texture_info[ 2 ]
                    s_setting = current_texture_info[ 3 ]
                    t_setting = current_texture_info[ 4 ]

                    if gfx_draw_list.render_settings.texture_settings[ 9 ] != s_setting or gfx_draw_list.render_settings.texture_settings[ 6 ] != t_setting:
                        #print( "Using texture with wrong overflow behavior!", gfx_draw_list.render_settings.current_texture )
                        pass

                    current_parent = getattr( self, 'texture_enable_group_' + str( self.layer_dict[ current_layer ] ) )
                    current_group = TextureBindGroup( current_texture, current_parent )
                else:
                    current_texture_image = pyglet.image.load( texture_filename )
                    ## We load everything to the atlas as well as to its own texture.  This is wasteful, but textures are so small, there's not much more overhead.  With upcoming pyglet 2.0, we'll be able to just add everything to a single texture atlas and then use shaders regardless of texture coordinate overflow behavior.
                    self.texture_atlas_dict[ texture_filename ] = self.texture_atlas.add( current_texture_image )
                    current_texture = current_texture_image.get_texture()
                    s_scale = current_texture_image.width
                    t_scale = current_texture_image.height
                    s_setting = gfx_draw_list.render_settings.texture_settings[ 9 ]
                    t_setting = gfx_draw_list.render_settings.texture_settings[ 6 ]

                    self.texture_group_dict[ texture_filename ] = [ current_texture, s_scale, t_scale, s_setting, t_setting ]

                    current_parent = getattr( self, 'texture_enable_group_' + str( self.layer_dict[ current_layer ] ) )
                    current_group = TextureBindGroup( current_texture, current_parent )

                    ## Bind the texture and change texture coordinate overflow settings
                    glEnable( GL_TEXTURE_2D )
                    glBindTexture( GL_TEXTURE_2D, current_texture.id )

                    if 'G_TX_CLAMP' in s_setting:
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE )
                    elif 'G_TX_MIRROR' in s_setting:
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_MIRRORED_REPEAT )
                    else:
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT )
                    if 'G_TX_CLAMP' in t_setting:
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE )
                    elif 'G_TX_MIRROR' in t_setting:
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_MIRRORED_REPEAT )
                    else:
                        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT )

            else:
                raise ValueError( "texture_dict missing texture!!!" )


            ## Convert N64 texel (ST-)coordinates to OpenGL (UV-) coordinates.
            texture_render_s_scale = gfx_draw_list.render_settings.texture_render_settings[ 0 ] / 65535
            texture_render_t_scale = gfx_draw_list.render_settings.texture_render_settings[ 1 ] / 65535
            for i in range( len( current_texels ) ):
                ## Fix s_scale.
                if i % 2 == 0:
                    current_texels[ i ] = texture_render_s_scale * current_texels[ i ] / s_scale

                ## Fix t_scale.
                else:
                    current_texels[ i ] = ( ( texture_render_t_scale * current_texels[ i ] / t_scale ) * ( - 1 ) + 1 )

            ## Check to see if the values of all texel coordinates are between 0 and 1.
            test_bool = True
            for i in current_texels:
                ## Kind of hacky, but some texture coordinates were clearly given wrong values.
                #if i > 1.02 or i < -0.032:
                if i > 1 or i < 0:
                    test_bool = False
                    break

            if test_bool and not gfx_draw_list.render_settings.geometry_mode.get( 'G_TEXTURE_GEN' ):
                ## Then we can use the texture_atlas version of the image.
                current_texture = self.texture_atlas_dict[ texture_filename ]
                current_parent = getattr( self, 'texture_enable_group_' + str( self.layer_dict[ current_layer ] ) )
                current_group = TextureBindGroup( current_texture, current_parent )

                ## Next, we have to convert our original texel coordinates to the coordinates of the texture region.
                region_tex_coords = current_texture.tex_coords
                region_s_min = region_tex_coords[ 0 ]
                region_s_max = region_tex_coords[ 3 ]
                region_t_min = region_tex_coords[ 1 ]
                region_t_max = region_tex_coords[ 7 ]
                for ind in range( 0, len( current_texels ), 2 ):
                    ## s-coordinate
                    current_texels[ ind ] = current_texels[ ind ] * ( region_s_max - region_s_min ) + region_s_min
                    ## t-coordinate
                    current_texels[ ind + 1 ] = current_texels[ ind + 1 ] * ( region_t_max - region_t_min ) + region_t_min


        current_positions = gfx_draw_list.positions.copy()
        current_positions = util_math.mat_to_positions( util_math.positions_to_mat( current_positions ) @ transformation_matrix )

        current_triangles = gfx_draw_list.triangles
        current_colours = gfx_draw_list.colors
        current_count = len( current_colours ) // 4

        current_render_group = RenderSettingsGroup( current_group, gfx_draw_list.render_settings.geometry_mode, gfx_draw_list.render_settings.current_lights, gfx_draw_list.render_settings.combine_mode, gfx_draw_list.render_settings.env_colour )

        if current_render_group.enable_lighting:
            ## Send normals to the GPU.
            current_normals = [ val for ind,val in enumerate( current_colours ) if ind % 4 != 3 ]
            ## Convert the list from unsigned representation of two's complement to floats.
            current_normals = util_math.convert_twos_comp_list( current_normals )
            current_normals = util_math.mat_to_positions( util_math.normalize( util_math.normals_to_mat( current_normals ) @ transformation_matrix ) )
            self.batch.add_indexed( current_count, GL_TRIANGLES, current_render_group, current_triangles, ( 'v3f', current_positions ), ( 't2f', current_texels ), ( 'n3f', current_normals ) )

        else:
            ## Send colours to the GPU.
            if gfx_draw_list.render_settings.env_colour is not None:
                ## Then we need to change the current_colours alphas to the alpha in env_colour.
                alpha = gfx_draw_list.render_settings.env_colour[ 3 ]
                for i in range( 3, len( current_colours ), 4 ):
                    current_colours[ i ] = alpha
            self.batch.add_indexed( current_count, GL_TRIANGLES, current_render_group, current_triangles, ( 'v3f', current_positions ), ( 't2f', current_texels ), ( 'c4B', current_colours ) )


    def add_painting_to_batch( self, painting, area_offset ):
        ## Painting_scale is a value that is hard coded into the game.  A painting is scaled by painting.size / painting_scale.
        painting_scale = 614.0
        rot_y_angle = painting.yaw
        rot_x_angle = painting.pitch
        translate_x = painting.posx
        translate_y = painting.posy
        translate_z = painting.posz
        translate_matrix = util_math.translate_mat( translate_x + area_offset[ 0 ], translate_y + area_offset[ 1 ], translate_z + area_offset[ 2 ] )
        scale_size = painting.size / painting_scale
        scale_matrix = util_math.scale_mat( scale_size )
        rot_x_matrix = util_math.rotate_around_x( rot_x_angle )
        rot_y_matrix = util_math.rotate_around_y( rot_y_angle )
        transformation_matrix = scale_matrix @ rot_y_matrix @ rot_x_matrix @ translate_matrix

        current_layer = painting.layer

        for each_gfx_draw_list in gfx_display_dict[ painting.normal_dl ]:
            self.add_drawlist_to_batch( each_gfx_draw_list, current_layer, transformation_matrix )



    def add_waterbox_to_batch( self, waterbox, area_offset ):
        current_layer = 'LAYER_TRANSPARENT_INTER'

        if texture_dict.get( waterbox.texture ) is not None:
            texture_filename = texture_dict[ waterbox.texture ]
            if self.texture_group_dict.get( texture_filename ):
                current_texture_info = self.texture_group_dict[ texture_filename ]
                current_texture = current_texture_info[ 0 ]
                s_scale = current_texture_info[ 1 ]
                t_scale = current_texture_info[ 2 ]
                s_setting = current_texture_info[ 3 ]
                t_setting = current_texture_info[ 4 ]

                ## Could this be the cause of the funny looking red sand texture in ssl?
                """
                if gfx_draw_list.render_settings.texture_settings[ 9 ] != s_setting or gfx_draw_list.render_settings.texture_settings[ 6 ] != t_setting:
                    print( "Using texture with wrong overflow behavior!", gfx_draw_list.render_settings.current_texture )
                """

                current_parent = getattr( self, 'texture_enable_group_' + str( self.layer_dict[ current_layer ] ) )
                current_group = TextureBindGroup( current_texture, current_parent )

            else:
                current_texture_image = pyglet.image.load( texture_filename )
                self.texture_atlas_dict[ texture_filename ] = self.texture_atlas.add( current_texture_image )
                current_texture = current_texture_image.get_texture()
                current_parent = getattr( self, 'texture_enable_group_' + str( self.layer_dict[ current_layer ] ) )
                current_group = TextureBindGroup( current_texture, current_parent )
                s_scale = current_texture_image.width
                t_scale = current_texture_image.height
                self.texture_group_dict[ texture_filename ] = [ current_texture, s_scale, t_scale, 'G_TX_WRAP | G_TX_NOMIRROR', 'G_TX_WRAP | G_TX_NOMIRROR' ]


        current_count = 4
        current_positions = area_offset * 4
        current_colours = []
        current_texels = []

        if waterbox.rotation_direction == 0:
            rot_offset = [ 0, 16384, -32768, -16384 ]
        elif waterbox.rotation_direction == 1:
            rot_offset = [ 0, -16384, -32768, 16384 ]
        
        for i in range( current_count ):

            vx, vy, vz = getattr( waterbox, 'vert' + str( 1 + i ) )
            current_positions[ 3 * i ] += vx
            current_positions[ 3 * i + 1 ] += vy
            current_positions[ 3 * i + 2 ] += vz
            
            s = ( 32 * waterbox.scale - 1.0 ) * math.sin( rot_offset[ i ] * math.pi  / 32768 )
            t = ( 32 * waterbox.scale - 1.0 ) * math.cos( rot_offset[ i ] * math.pi  / 32768 )
            current_texels += [ s, t ]

            #current_colours += [ 255, 255, 255, waterbox.alpha ]
            current_colours += waterbox.colour


        for i in range( len( current_texels ) ):
            ## Fix s_scale.
            if i % 2 == 0:
                current_texels[ i ] = current_texels[ i ] / s_scale

            ## Fix t_scale.
            else:
                current_texels[ i ] = ( current_texels[ i ] / t_scale ) * ( - 1 ) + 1

        current_triangles = [ 0, 1, 2, 0, 2, 3 ]

        self.batch.add_indexed( current_count, GL_TRIANGLES, current_group, current_triangles, ( 'v3f', current_positions ), ( 't2f', current_texels ), ( 'c4B', current_colours ) )


    def add_movtex_tri_to_batch( self, each_movtex_obj, current_area_offset ):
        transformation_matrix = util_math.translate_mat( current_area_offset[ 0 ], current_area_offset[ 1 ], current_area_offset[ 2 ] )
        self.add_drawlist_to_batch( each_movtex_obj.drawlist, each_movtex_obj.layer, transformation_matrix )



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
        #config = None

        ## Set screen resolution.
        self.max_x_res = pyglet.canvas.get_display().get_default_screen().width
        self.max_y_res = pyglet.canvas.get_display().get_default_screen().height
        self.set_resolution()

        super().__init__( self.x_res, self.y_res, "Mario 64", resizable=resizable, vsync=vsync, fullscreen=fullscreen, config=config )
        ## Is this line needed?
        #self.register_event_type( 'on_pause' )

        self.set_exclusive_mouse( False )

        self.set_opengl_state()

        self.level_geometry = Geometry()
        self.level_geometry.toggle_group_textures( self.load_textures )

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
        self.start_area, self.start_yaw, *self.start_pos = level_scripts[ self.current_level ].mario_pos
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
        if skybox_dict[ level ]:
            self.skybox = Skybox( skybox_dict[ level ], self.mario_graphics_dir )
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
            #self.fps_display.set_fps( pyglet.clock.get_fps() )
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

    mario_graphics_dir = Path( os.path.realpath( __file__ ) ).parent
    pickle_dir = mario_graphics_dir / 'pickles'

    with open( pickle_dir / 'model_dicts.pickle', 'rb' ) as f:
        model_dict, macro_dict, macro_to_geo_dict, special_dict = pickle.load( f )
    
    with open( pickle_dir / 'm64_dicts.pickle', 'rb' ) as f:
        skybox_dict, texture_dict, name_dict = pickle.load( f )
    
    with open( pickle_dir / 'level_scripts.pickle', 'rb' ) as f:
        level_scripts = pickle.load( f )

    with open( pickle_dir / 'draw_dicts.pickle', 'rb' ) as f:
        vtx_dict, gfx_dict, light_dict, gfx_display_dict = pickle.load( f )

    with open( pickle_dir / 'obj_geo_dicts.pickle', 'rb' ) as f:
        obj_name_to_geo_dict, geo_dict = pickle.load( f )

    font_filename = 'super-mario-64.ttf'
    font_name = 'Super Mario 64'
    font_path = str( ( mario_graphics_dir / 'fonts' / font_filename ).resolve() )
    pyglet.font.add_file( font_path )

    screenshot_dir = mario_graphics_dir / 'screenshots'
    os.makedirs( screenshot_dir, exist_ok=True )

    game_window = GameWindow( mario_graphics_dir, fullscreen=False, y_inv=False, vsync=False, resizable=True, load_textures=True, wireframe=False, load_skyboxes=True, original_res=False, show_fps=False, font=font_name )
    #game_window = GameWindow( mario_graphics_dir, fullscreen=True, y_inv=False, vsync=True, resizable=True, load_textures=True, wireframe=False, load_skyboxes=True, original_res=False, show_fps=False )

    ## Main game loop
    pyglet.app.run()

import math
import pyglet
from pyglet.gl import *

from parsers.level_script_parser import LevelScript, LevelGeo, LevelGeoDisplayList, Area, Obj, WaterBox
from parsers.level_fixes import get_extra_scale
from parsers.geo_parser import Geo, GeoDisplayList, Animation
from parsers.model_parser import Vertex, Vtx, Gfx, GfxDrawList, Light, RenderSettings
from parsers.movtex_tri_parser import Movtex_Tri

import util_math
from groups import TextureEnableGroup, TextureBindGroup, Layer0Group, Layer1Group, Layer2Group, Layer3Group, Layer4Group, Layer5Group, Layer6Group, Layer7Group, RenderSettingsGroup



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

            ## Next, load any plain objects.
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



from pathlib import Path
import math
import pickle

from .level_script_parser import LevelScript, LevelGeo, LevelGeoDisplayList, Area, Obj, WaterBox
from .model_parser import Vertex, Vtx, Gfx, GfxDrawList, Light, RenderSettings
from .geo_parser import Geo, GeoDisplayList, Animation
from .movtex_tri_parser import Movtex_Tri
from .paintings_parser import Painting
import util_math



def get_extra_scale( obj_name, obj_beh, obj_behparam, obj_geo ):
    """
    Objects in the game can have their size scaled in many different ways.  While this program correctly parses scale changes in geo files, scale can also be changed in multiple ways with multiple syntaxes in behaviors, which are basically custom functions for each actor.  Correctly parsing behaviors would essentially require a C to Python translator that works on the entire Mario 64 codebase since behaviors use globals and also take in arguments from all over the source code.  As such, from the point of view of this program, scale is hardcoded in the source for some objects.  To properly display objects at the correct scale, we use this function as lookup.
    """
    scale_dict = { 'exclamation_box_geo': 2.0, 'wing_cap_box_geo': 2.0, 'vanish_cap_box_geo': 2.0, 'metal_cap_box_geo': 2.0, 'wooden_post_geo': 0.5, 'macro_goomba':1.5, 'macro_huge_goomba':3.5, 'macro_tiny_goomba':0.5, 'macro_chuckya':2.0, 'macro_blue_coin_switch':3.0, 'MODEL_CAP_SWITCH':0.5, 'macro_breakable_box_small':0.4, 'macro_heave_ho':2.0, 'MODEL_THWOMP':1.4, 'macro_fire_spitter':0.2, 'MODEL_UNAGI':3.0, 'MODEL_WIGGLER_HEAD':4.0, 'bhvTuxiesMother':4.0, 'MODEL_BOO':2.0, 'MODEL_KOOPA_WITH_SHELL':1.5, 'macro_chain_chomp':2.0, 'MODEL_WHOMP':2.0, 'MODEL_MANTA_RAY':2.5, 'MODEL_PURPLE_SWITCH':1.5, 0x01020000:3.0, 0x02030000:3.0, 'MODEL_CCM_SNOWMAN_BASE':1.0, 'MODEL_BULLET_BILL':0.4, 'bhvSLWalkingPenguin':6.0, 'bhvRacingPenguin':4.0, 'bhvBalconyBigBoo':3.0, 'bhvGhostHuntBigBoo':3.0, 'bhvWaterMist2':21.0, 'bhvFlame':7.0, 'bhvBird':0.7, 'bhvBubba':0.5, 'MODEL_FLYGUY':1.5, 'MODEL_MONTY_MOLE':1.5, }
    if scale_dict.get( obj_behparam ) is not None:
        return scale_dict.get( obj_behparam )

    if scale_dict.get( obj_beh ) is not None:
        return scale_dict.get( obj_beh )

    if scale_dict.get( obj_name ) is not None:
        return scale_dict.get( obj_name )

    if scale_dict.get( obj_geo ) is not None:
        return scale_dict.get( obj_geo )


def move_level_area( level_scripts, level, area, new_position ):
    """
    Level is a string like 'castle_inside' or 'bob'.
    area is a number corresponding to the area to move.  Areas are counted 1 up, so the primary area in a level is 1.  It's best to level area 1 fixed and just move other areas.
    new_position is an array of length 3 of numbers corresponding to the x, y, z offset coordinates.
    """
    level_scripts[ level ].areas[ area - 1 ].offset = new_position


def set_start_look( level_scripts, level, yaw ):
    level_scripts[ level ].mario_pos[ 1 ] = yaw


def fix_start_looks( level_scripts ):
    set_start_look( level_scripts, 'castle_grounds', 0 )
    set_start_look( level_scripts, 'castle_inside', 0 )
    set_start_look( level_scripts, 'bob', 70 )
    set_start_look( level_scripts, 'wf', 65 )
    set_start_look( level_scripts, 'jrb', 120 )
    set_start_look( level_scripts, 'ccm', 115 )
    set_start_look( level_scripts, 'bbh', 0 )
    set_start_look( level_scripts, 'hmc', 45 )
    set_start_look( level_scripts, 'ddd', 90 )
    set_start_look( level_scripts, 'wdw', 270 )
    set_start_look( level_scripts, 'ttm', 70 )
    set_start_look( level_scripts, 'thi', 35 )
    set_start_look( level_scripts, 'vcutm', 180 )
    set_start_look( level_scripts, 'bowser_1', 0 )
    set_start_look( level_scripts, 'bowser_2', 0 )
    set_start_look( level_scripts, 'bowser_3', 0 )


def fix_level_area_offsets( level_scripts ):
    """
    Because the game is normally designed to have one area loaded at a time and this program can load all areas of a level simultaneously, some choices have to be made about how areas align with one another.  In some cases, things can be lined up perfectly with no compromises, like in ddd.  In other cases, lining things up areas causes clipping issues.  This function moves level areas for all levels with multiple areas.  Levels with multiple areas:
    castle_inside: 3
    jrb: 2
    ccm: 2
    lll: 2
    ssl: 3
    ddd: 2
    sl: 2
    wdw: 2
    ttm: 4
    thi: 3
    """
    ## castle_inside has three areas: 1 is main floor, 2 is upstairs, 3 is basement.  Main floor and basement line up naturally, however upstairs overlaps with main floor.  Unfortunately, it's not possible to link up the main floor with the upstairs without them intersecting.  The offset to match up area 1 and area 2 is [ 0, 0, -4095 ].  However, the floors will clip into one another.  Instead, just add some height to the upstairs so that floors don't clip.  1230 is the minimum height that can badded without clipping.
    move_level_area( level_scripts, 'castle_inside', 2, [ 0, 1230, -4095 ] )

    ## jrb has two areas: 1 is the main area including cave.  2 is the inside of the sunken ship with the treasure chest puzzle.
    ## Moves the sunken ship and its associated waterbox out of the main area.
    move_level_area( level_scripts, 'jrb', 2, [ 0, 0, -4500 ] )

    ## ccm has two areas: 1 the mountain, 2 the slide.
    move_level_area( level_scripts, 'ccm', 2, [ 0, 0, -17000 ] )

    ## lll has two areas: 1 is the main area, 2 is inside of the volcano.
    move_level_area( level_scripts, 'lll', 2, [ 0, -7250, 0 ] )

    ## ssl has three areas: 1 is the main area, 2 is inside the pyramid, and 3 is Eyerok's arena.
    ## Note that areas 2 and 3 are already aligned, so move them both by the same amount.
    ## This offset cleanly combines all areas and was arrived at by trial and error.
    move_level_area( level_scripts, 'ssl', 2, [ -2047, -5375, -1279 ] )
    move_level_area( level_scripts, 'ssl', 3, [ -2047, -5375, -1279 ] )

    ## ddd has two areas: 1 is the area you load into with the eel.  2 is the area with the submarine.  This level can be perfectly put together.
    ## This moves the submarine area over so that the level links up perfectly.  The offset value is pulled directly from an instant warp in the ddd level script.
    move_level_area( level_scripts, 'ddd', 2, [ 8192, 0, 0 ] )

    ## sl has two areas: 1 is the main area, 2 is inside the igloo.  The inside of the igloo is below the level by default.
    ## This small shift just prevents the igloo area from clipping into the ground of area 1.
    move_level_area( level_scripts, 'sl', 2, [ 0, 0, 200 ] )

    ## wdw has two areas: 1 is the main area, 2 is the city.  They join up in the tunnel.  Unfortunately, area 2 clips upward through the floor of area 1.  We can move area 2 downward to avoid this clipping, but this then breaks the tunnel.
    move_level_area( level_scripts, 'wdw', 2, [ 0, 0, 0 ] )

    ## ttm has four areas: 1 is the mountain.  2, 3, and 4 are all the slide.  There are 2 instant warps that take you from area 2 to 3 and area 3 to 4.  We can pull the values of the instant warps from the ttm level script.  Finally, the slide is offset by a large fixed amount so that it doesn't clip with the mountain.
    slide_offset = [ 0, 0, -10000 ]
    ## Changing these two lines would break the slide.
    area_2_from_3_offset = [ -10240, -7168, -10240 ]
    area_3_from_4_offset = [ 11264, -13312, -3072 ]

    move_level_area( level_scripts, 'ttm', 2, [ slide_offset[ 0 ], slide_offset[ 1 ], slide_offset[ 2 ] ] )
    move_level_area( level_scripts, 'ttm', 3, [ area_2_from_3_offset[ 0 ] + slide_offset[ 0 ], area_2_from_3_offset[ 1 ] + slide_offset[ 1 ], area_2_from_3_offset[ 2 ] + slide_offset[ 2 ] ] )
    move_level_area( level_scripts, 'ttm', 4, [ area_2_from_3_offset[ 0 ] + area_3_from_4_offset[ 0 ] + slide_offset[ 0 ], area_2_from_3_offset[ 1 ] + area_3_from_4_offset[ 1 ] + slide_offset[ 1 ], area_2_from_3_offset[ 2 ] + area_3_from_4_offset[ 2 ] + slide_offset[ 2 ] ] )

    ## thi has three areas: 1 is huge island, 2 is tiny island, 3 is the inside of the mountain where the red coins/wiggler are.
    move_level_area( level_scripts, 'thi', 2, [ -18000, -2500, 0 ] )
    ## Unfortunately, area 1 and area 3 can't be perfectly lined up.  You can either match up the hole on top of the mountain with the hole at the top of the wiggler's area, or you can match up the entrance/exit to the red coin area, but you can't do both.  x = 0 will match up the former, x = -102 will match up the latter.
    move_level_area( level_scripts, 'thi', 3, [ -102, -1535, -1532 ] )


def dedupe_level_draw_calls( level_scripts ):
    """
    Dedupes level draw calls per area.  The only levels that need to be deduped are hmc, bbh, and castle_inside.  This is a result of each level using rooms.  Additionally, hmc and bbh are both one area levels, so we can just dedupe everything.  However, castle_inside has three areas, so we dedupe by area.
    """
    ## easiest to dedupe geo_dls by geo_dl.dl_name
    ## make an empty dict to keep track of seen dl_names.
    ## iterate through by area, then by geo, look up into level_scripts[ level_name ].geo_dict, and then iterate through each_geo_dl in that, inspect each_geo_dl.dl_name, and dedupe
    for each_level in level_scripts:
        for each_area in level_scripts[ each_level ].areas:
            seen_geo_dls = {}
            for each_geo in each_area.geo:
                geo_dl_list = level_scripts[ each_level ].geo_dict[ each_geo ].geo_dls
                for i in range( len( geo_dl_list ) - 1, -1, -1 ):
                    each_geo_dl = geo_dl_list[ i ]
                    if seen_geo_dls.get( each_geo_dl.dl_name ) is not None:
                        del geo_dl_list[ i ]
                        #print( "Deleted geo_dl:", each_geo_dl.dl_name )
                    else:
                        seen_geo_dls[ each_geo_dl.dl_name ] = 1


def remove_bbh_opaque_wall_and_ceiling( level_scripts, gfx_display_dict ):
    """
    Because bbh is broken up into rooms, there is one wall and one ceiling that were put in place to prevent the player from seeing other rooms that they're not supposed to see.  Since we're loading everything at once, we remove the wall and ceiling from gfx_display_list.
    """
    for each_area in level_scripts[ 'bbh' ].areas:
        for each_geo in each_area.geo:
            for each_geo_dl in level_scripts[ 'bbh' ].geo_dict[ each_geo ].geo_dls:
                gfx_display_list = gfx_display_dict[ each_geo_dl.dl_name ]
                for i in range( len( gfx_display_list ) - 1, -1, -1 ):
                    if gfx_display_list[ i ].name == 'bbh_seg7_vertex_0701D980':
                        del gfx_display_list[ i ]
                    elif gfx_display_list[ i ].name == 'bbh_seg7_vertex_07019508':
                        del gfx_display_list[ i ]


def remove_castle_basement_tile( level_scripts, gfx_display_dict ):
    """
    Because all areas are loaded at once, tiles from the basement area overlap with tiles from the first floor area, causing z-fighting.  This removes the tiles from the first floor area by updating gfx_display_list.
    Delete alls vertices in inside_castle_seg7_vertex_0702C570 that have a y value of -1074.  Also basically recreates a new GfxDrawList with the remaining vertices.
    """
    for each_area in level_scripts[ 'castle_inside' ].areas:
        for each_geo in each_area.geo:
            for each_geo_dl in level_scripts[ 'castle_inside' ].geo_dict[ each_geo ].geo_dls:
                gfx_display_list = gfx_display_dict[ each_geo_dl.dl_name ]
                for i in range( len( gfx_display_list ) - 1, -1, -1 ):
                    if gfx_display_list[ i ].name == 'inside_castle_seg7_vertex_0702C570':
                        new_positions = []
                        new_texel_coordinates = []
                        new_colours = []
                        new_triangles = []
                        old_pos_to_new_pos = {}
                        for j in range( len( gfx_display_list[ i ].positions ) // 3 ):
                            if gfx_display_list[ i ].positions[ 3 * j + 1 ] != -1074:
                                old_pos_to_new_pos[ j ] = len( new_positions ) // 3
                                new_positions += gfx_display_list[ i ].positions[ 3 * j : 3 * ( j + 1 ) ]
                                new_texel_coordinates += gfx_display_list[ i ].texel_coordinates[ 2 * j : 2 * ( j + 1 ) ]
                                new_colours += gfx_display_list[ i ].colors[ 4 * j : 4 * ( j + 1 ) ]

                        for j in range( len( gfx_display_list[ i ].triangles ) ):
                            if gfx_display_list[ i ].triangles[ j ] in old_pos_to_new_pos.keys():
                                new_triangles.append( old_pos_to_new_pos[ gfx_display_list[ i ].triangles[ j ] ] ) 
                        gfx_display_list[ i ].positions = new_positions
                        gfx_display_list[ i ].texel_coordinates = new_texel_coordinates
                        gfx_display_list[ i ].colors = new_colours
                        gfx_display_list[ i ].triangles = new_triangles


def add_castle_lobby_light( level_scripts ):
    ## Add dl_castle_lobby_wing_cap_light to castle_geo_000F30.
    wing_cap_light_geo_dl = LevelGeoDisplayList( 'GEO_DISPLAY_LIST(LAYER_TRANSPARENT, dl_castle_lobby_wing_cap_light)' )
    level_scripts[ 'castle_inside' ].geo_dict[ level_scripts[ 'castle_inside' ].areas[ 0 ].geo[ 0 ] ].geo_dls.append( wing_cap_light_geo_dl )


def make_castle_inside_mirror_transparent( level_scripts, gfx_display_dict ):
    for each_area in level_scripts[ 'castle_inside' ].areas:
        for each_geo in each_area.geo:
            for each_geo_dl in level_scripts[ 'castle_inside' ].geo_dict[ each_geo ].geo_dls:
                gfx_display_list = gfx_display_dict[ each_geo_dl.dl_name ]
                for i in range( len( gfx_display_list ) - 1, -1, -1 ):
                    if gfx_display_list[ i ].name == 'inside_castle_seg7_vertex_0704A1D0':
                        gfx_display_list[ i ].render_settings.env_colour = ( 255, 255, 255, 75 )



def fix_intro_dls( gfx_display_dict ):
    for gfx_display_list in gfx_display_dict[ 'intro_seg7_dl_0700B3A0' ] + gfx_display_dict[ 'intro_seg7_dl_0700C6A0' ]:
        ## Fix incorrect lighting values for the copyright.
        if gfx_display_list.render_settings.geometry_mode[ 'G_LIGHTING' ] == True:
            gfx_display_list.render_settings.geometry_mode[ 'G_LIGHTING' ] = False

        ## Fix Nintendo logo and resize/reposition it.
        if gfx_display_list.name == 'intro_seg7_vertex_0700B420':
            gfx_display_list.texture_enable = True
            gfx_display_list.render_settings.current_texture = 'intro_seg7_texture_0700B4A0'
            gfx_display_list.render_settings.set_current_texture_settings( 'gsDPSetTile(G_IM_FMT_RGBA, G_IM_SIZ_16b, 16, 0, G_TX_RENDERTILE, 0, G_TX_CLAMP, 7, G_TX_NOLOAD, G_TX_CLAMP, 4, G_TX_NOLOD)' )
            ninlogo_center_x = 0
            ninlogo_center_y = -500
            ninlogo_center_z = -1
            ninlogo_width = 1280
            ninlogo_height = 160

            x_remap = { 96:( ninlogo_center_x - ninlogo_width / 2 ), 224:( ninlogo_center_x + ninlogo_width / 2 ) }
            y_remap = { 42:( ninlogo_center_y - ninlogo_height / 2 ), 58:( ninlogo_center_y + ninlogo_height / 2 ) }

            try:
                for i in range( len( gfx_display_list.positions ) ):
                    if i % 3 == 0:
                        gfx_display_list.positions[ i ] = x_remap[ gfx_display_list.positions[ i ] ]
                    if i % 3 == 1:
                        gfx_display_list.positions[ i ] = y_remap[ gfx_display_list.positions[ i ] ]

            except:
                pass


        ## Fix TM sign
        elif gfx_display_list.name == 'intro_seg7_vertex_0700B460':
            gfx_display_list.texture_enable = True
            gfx_display_list.render_settings.current_texture = 'intro_seg7_texture_0700C4A0'
            gfx_display_list.render_settings.set_current_texture_settings( 'gsDPSetTile(G_IM_FMT_RGBA, G_IM_SIZ_16b, 16, 0, G_TX_RENDERTILE, 0, G_TX_CLAMP, 4, G_TX_NOLOAD, G_TX_CLAMP, 4, G_TX_NOLOD)' )

        ## Remove black square background for behind the main logo.
        elif gfx_display_list.name == 'intro_seg7_vertex_07006AC0':
            new_positions = []
            new_texel_coordinates = []
            new_colours = []
            new_triangles = []
            old_pos_to_new_pos = {}
            for j in range( len( gfx_display_list.positions ) // 3 ):
                if gfx_display_list.positions[ 3 * j + 2 ] != -818:
                    old_pos_to_new_pos[ j ] = len( new_positions ) // 3
                    new_positions += gfx_display_list.positions[ 3 * j : 3 * ( j + 1 ) ]
                    new_texel_coordinates += gfx_display_list.texel_coordinates[ 2 * j : 2 * ( j + 1 ) ]
                    new_colours += gfx_display_list.colors[ 4 * j : 4 * ( j + 1 ) ]

            for j in range( len( gfx_display_list.triangles ) ):
                if gfx_display_list.triangles[ j ] in old_pos_to_new_pos.keys():
                    new_triangles.append( old_pos_to_new_pos[ gfx_display_list.triangles[ j ] ] ) 
            gfx_display_list.positions = new_positions
            gfx_display_list.texel_coordinates = new_texel_coordinates
            gfx_display_list.colors = new_colours
            gfx_display_list.triangles = new_triangles



def place_painting_in_level_area( painting_name, level, area, level_scripts, paintings_dict ):
    painting = paintings_dict[ painting_name ]
    area_number = area - 1
    level_scripts[ level ].areas[ area_number ].paintings.append( painting )


def place_paintings( level_scripts, paintings_dict ):
    ## Castle inside regular paintings
    place_painting_in_level_area( 'bob_painting', 'castle_inside', 1, level_scripts, paintings_dict )
    place_painting_in_level_area( 'wf_painting', 'castle_inside', 1, level_scripts, paintings_dict )
    place_painting_in_level_area( 'jrb_painting', 'castle_inside', 1, level_scripts, paintings_dict )
    place_painting_in_level_area( 'ccm_painting', 'castle_inside', 1, level_scripts, paintings_dict )
    place_painting_in_level_area( 'lll_painting', 'castle_inside', 3, level_scripts, paintings_dict )
    place_painting_in_level_area( 'ssl_painting', 'castle_inside', 3, level_scripts, paintings_dict )
    place_painting_in_level_area( 'sl_painting', 'castle_inside', 2, level_scripts, paintings_dict )
    place_painting_in_level_area( 'wdw_painting', 'castle_inside', 2, level_scripts, paintings_dict )
    place_painting_in_level_area( 'ttm_painting', 'castle_inside', 2, level_scripts, paintings_dict )
    place_painting_in_level_area( 'thi_tiny_painting', 'castle_inside', 2, level_scripts, paintings_dict )
    place_painting_in_level_area( 'thi_huge_painting', 'castle_inside', 2, level_scripts, paintings_dict )
    place_painting_in_level_area( 'ttc_painting', 'castle_inside', 2, level_scripts, paintings_dict )

    ## Slide painting in ttm
    place_painting_in_level_area( 'ttm_slide_painting', 'ttm', 1, level_scripts, paintings_dict )

    ## Need to deal with these separately.  These paintings don't have a proper normal display list because they're always rippling.
    #place_painting_in_level_area( 'hmc_painting', 'castle_inside', 3, level_scripts, gfx_display_dict, paintings_dict )
    #place_painting_in_level_area( 'ddd_painting', 'castle_inside', 3, level_scripts, gfx_display_dict, paintings_dict )
    #place_painting_in_level_area( 'cotmc_painting', 'hmc', 1, level_scripts, gfx_display_dict, paintings_dict )

  

def fix_waterbox_colours( level_scripts ):
    ## Make the toxic mist waterboxes in hmc yellow.
    level_scripts[ 'hmc' ].areas[ 0 ].movtex[ 1 ].colour = [ 255, 255, 0, 120 ]
    level_scripts[ 'hmc' ].areas[ 0 ].movtex[ 2 ].colour = [ 255, 255, 0, 180 ]

    ## Make the toxbox quicksand waterboxes in ssl red.
    level_scripts[ 'ssl' ].areas[ 0 ].movtex[ 1 ].colour = [ 255, 0, 0, 150 ]
    level_scripts[ 'ssl' ].areas[ 0 ].movtex[ 2 ].colour = [ 255, 0, 0, 150 ]


def place_movtexs( level_scripts, movtex_dict ):
    ## castle_grounds
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_CASTLE_WATERFALL', 'castle_grounds', 1 )

    ## ssl
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_SSL_PYRAMID_SIDE', 'ssl', 1 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_SSL_PYRAMID_CORNER', 'ssl', 1 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_SSL_COURSE_EDGE', 'ssl', 1 )
    place_sand_pits_outside( level_scripts, movtex_dict )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_PYRAMID_SAND_PATHWAY_FRONT', 'ssl', 2 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_PYRAMID_SAND_PATHWAY_FLOOR', 'ssl', 2 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_PYRAMID_SAND_PATHWAY_SIDE', 'ssl', 2 )
    place_sand_pits_pyramid( level_scripts, movtex_dict )

    ## bitfs
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_BITFS_LAVA_FIRST', 'bitfs', 1 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_BITFS_LAVA_SECOND', 'bitfs', 1 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_BITFS_LAVA_FLOOR', 'bitfs', 1 )

    ## lll
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_LLL_LAVA_FLOOR', 'lll', 1 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_VOLCANO_LAVA_FALL', 'lll', 2 )

    ## cotmc
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_COTMC_WATER', 'cotmc', 1 )

    ## ttm
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_TTM_BEGIN_WATERFALL', 'ttm', 1 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_TTM_END_WATERFALL', 'ttm', 1 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_TTM_BEGIN_PUDDLE_WATERFALL', 'ttm', 1 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_TTM_END_PUDDLE_WATERFALL', 'ttm', 1 )
    place_movtex_in_level( level_scripts, movtex_dict, 'MOVTEX_TTM_PUDDLE_WATERFALL', 'ttm', 1 )

    ## ttc
    place_treadmills_ttc( level_scripts, movtex_dict )


def place_treadmills_ttc( level_scripts, movtex_dict ):
    yaw_and_positions = [ [ 135, -139, -4408, -1056 ], [ 45, 1313, 6190, 1313 ], [ 90, 618, 3656, 148 ], [ 270, 963, 3297, 608 ], [ 90, 1306, 2939, 1069 ], [ 315, -1179, -1453, -792 ], [ 0, 1851, -2488, -98 ] ]
    for i in range( 0, 2 ):
        current_large_treadmill = movtex_dict[ 'MOVTEX_TREADMILL_BIG' ].copy()
        current_yaw = yaw_and_positions[ i ][ 0 ]
        current_offset = yaw_and_positions[ i ][ 1 : ]
        positions_mat = util_math.positions_to_mat( current_large_treadmill.drawlist.positions )
        rotate_yaw_mat = util_math.rotate_around_y( current_yaw )
        move_mat = util_math.translate_mat( *current_offset )
        current_large_treadmill.drawlist.positions = util_math.mat_to_positions( positions_mat @ rotate_yaw_mat @ move_mat )
        level_scripts[ 'ttc' ].areas[ 0 ].movtex += [ current_large_treadmill ]

    for i in range( 2, 7 ):
        current_small_treadmill = movtex_dict[ 'MOVTEX_TREADMILL_SMALL' ].copy()
        current_yaw = yaw_and_positions[ i ][ 0 ]
        current_offset = yaw_and_positions[ i ][ 1 : ]
        positions_mat = util_math.positions_to_mat( current_small_treadmill.drawlist.positions )
        rotate_yaw_mat = util_math.rotate_around_y( current_yaw )
        move_mat = util_math.translate_mat( *current_offset )
        current_small_treadmill.drawlist.positions = util_math.mat_to_positions( positions_mat @ rotate_yaw_mat @ move_mat )
        level_scripts[ 'ttc' ].areas[ 0 ].movtex += [ current_small_treadmill ]


def place_sand_pits_pyramid( level_scripts, movtex_dict ):
    ## In ssl, the sand pits are actually part of the level geometry and are placed as objects with positions.  We need to adjust these positions and place the objects in the appropriate spot.
    area_number = 2 - 1
    positions = [ [ 1741,  -101,  1843 ], [ 0,  -101,   528 ], [ -1740,  -101,  1843 ] ]
    sand_pits = []
    for i in range( 3 ):
        current_sand_pit = movtex_dict[ 'MOVTEX_SSL_SAND_PIT_PYRAMID' ].copy()
        current_offset = positions[ i ]
        for j in range( len( current_sand_pit.drawlist.positions ) ):
            current_sand_pit.drawlist.positions[ j ] += current_offset[ j % 3 ]
        sand_pits.append( current_sand_pit )
    level_scripts[ 'ssl' ].areas[ area_number ].movtex += sand_pits


def place_sand_pits_outside( level_scripts, movtex_dict ):
    area_number = 1 - 1
    positions = [ [ 5760,  0,  5751 ], [ -3583,  0,  2935 ], [ -511,  0,  2935 ], [ 1024,  0,  3822 ], [ 3072,  0,   375 ] ]
    sand_pits = []
    for i in range( 5 ):
        current_sand_pit = movtex_dict[ 'MOVTEX_SSL_SAND_PIT_OUTSIDE' ].copy()
        current_offset = positions[ i ]
        for j in range( len( current_sand_pit.drawlist.positions ) ):
            current_sand_pit.drawlist.positions[ j ] += current_offset[ j % 3 ]
        sand_pits.append( current_sand_pit )

    level_scripts[ 'ssl' ].areas[ area_number ].movtex += sand_pits


def place_movtex_in_level( level_scripts, movtex_dict, movtex, level, area ):
    area_number = area - 1
    level_scripts[ level ].areas[ area_number ].movtex.append( movtex_dict[ movtex ] )


def find_dorrie( level_scripts ):
    for each_obj in level_scripts[ 'hmc' ].areas[ 0 ].objs:
        if each_obj.model == 'MODEL_DORRIE':
            ## Dorrie's x position is initially -3533.  In Dorrie's behavior on spawn, 2000 gets added to x.
            each_obj.position[ 0 ] = -3533 + 2000


def fix_jrb_act_objs( level_scripts ):
    obj_to_remove = []
    for each_obj in level_scripts[ 'jrb' ].areas[ 0 ].objs_with_acts:
        if each_obj.acts == [ '1' ]:
            obj_to_remove.append( each_obj )

    for each_obj in obj_to_remove:
        level_scripts[ 'jrb' ].areas[ 0 ].objs_with_acts.remove( each_obj )


def spawn_treasure_chest( level_scripts, level, area, x, y, z, rotx, roty, rotz ):
    lid_y = y + 102
    roty_deg = math.pi * roty / 180
    lid_x = round( x + -77 * math.sin( roty_deg ) )
    lid_z = round( z + -77 * math.cos( roty_deg ) )
    tc_obj_str = 'OBJECT( MODEL_TREASURE_CHEST_BASE, ' + str( x ) + ', ' + str( y ) + ', ' + str( z ) + ', ' + str( rotx ) + ', ' + str( roty ) + ', ' + str( rotz ) + ', None, bhvTreasureChestBottom )'
    tc_lid_obj_str = 'OBJECT( MODEL_TREASURE_CHEST_LID, ' + str( lid_x ) + ', ' + str( lid_y ) + ', ' + str( lid_z ) + ', ' + str( rotx ) + ', ' + str( roty ) + ', ' + str( rotz ) + ', 0, bhvTreasureChestTop )'
    tc = Obj( tc_obj_str )
    tc_lid = Obj( tc_lid_obj_str )

    area_number = area - 1
    level_scripts[ level ].areas[ area_number ].objs.append( tc )
    level_scripts[ level ].areas[ area_number ].objs.append( tc_lid )


def add_treasure_chests_to_jrb( level_scripts ):
    spawn_treasure_chest( level_scripts, 'jrb', 1, -1700, -2812, -1150, 0, 180, 0 )
    spawn_treasure_chest( level_scripts, 'jrb', 1, -1150, -2812, -1550, 0, 180, 0 )
    spawn_treasure_chest( level_scripts, 'jrb', 1, -2400, -2812, -1800, 0, 180, 0 )
    spawn_treasure_chest( level_scripts, 'jrb', 1, -1800, -2812, -2100, 0, 180, 0 )
    spawn_treasure_chest( level_scripts, 'jrb', 2, 400, -350, -2700, 0, 0, 0 )
    spawn_treasure_chest( level_scripts, 'jrb', 2, 650, -350, -940, 0, -135, 0 )
    spawn_treasure_chest( level_scripts, 'jrb', 2, -550, -350, -770, 0, 135, 0 )
    spawn_treasure_chest( level_scripts, 'jrb', 2, 100, -350, -1700, 0, 0, 0 )
    spawn_treasure_chest( level_scripts, 'ddd', 1, -4500, -5119, 1300, 0, -135, 0 )
    spawn_treasure_chest( level_scripts, 'ddd', 1, -1800, -5119, 1050, 0, 45, 0 )
    spawn_treasure_chest( level_scripts, 'ddd', 1, -4500, -5119, -1100, 0, 50, 0 )
    spawn_treasure_chest( level_scripts, 'ddd', 1, -2400, -4607, 125, 0, 88, 0 )


def add_peach_to_castle_grounds( level_scripts ):
    level_scripts[ 'castle_grounds' ].areas[ 0 ].objs.append( Obj( 'OBJECT( MODEL_PEACH, -200, 3174, -5600, 0, 45, 0, None, None' ) )


def add_puzzle_piece( level_scripts, model, x, z, beh ):
    piece_width = 480
    puzzle_position = [ -5119,  102,  1024 ]
    piece_x = round( puzzle_position[ 0 ] + x * piece_width / 10 )
    piece_y = round( puzzle_position[ 1 ] + 50 )
    piece_z = round( puzzle_position[ 2 ] + z * piece_width / 10 )
    obj_str = 'OBJECT( ' + model + ', ' + str( piece_x ) + ', ' + str( piece_y ) + ', ' + str( piece_z ) + ', ' + '0' + ', ' + '0' + ', ' + '0' + ', None, ' + beh + ' )'
    level_scripts[ 'lll' ].areas[ 0 ].objs.append( Obj( obj_str ) )


def place_lll_puzzle_pieces( level_scripts ):
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_1', -5, -15, 'sPieceActions01' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_2', 5, -15, 'sPieceActions02' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_3', -15, -5, 'sPieceActions03' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_4', -5, -5, 'sPieceActions04' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_5', 5, -5, 'sPieceActions05' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_6', 15, -5, 'sPieceActions06' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_7', -15, 5, 'sPieceActions07' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_8', -5, 5, 'sPieceActions08' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_9', 5, 5, 'sPieceActions09' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_10', 15, 5, 'sPieceActions10' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_11', -15, 15, 'sPieceActions11' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_12', -5, 15, 'sPieceActions12' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_13', 5, 15, 'sPieceActions13' )
    add_puzzle_piece( level_scripts, 'MODEL_LLL_BOWSER_PIECE_14', 15, 15, 'sPieceActions14' )


def add_koopa_flags( level_scripts ):
    bob_flag_str = 'OBJECT( MODEL_KOOPA_FLAG, 3304, 4242, -4603, 0, 0, 0, 0, bhvKoopaFlag )'
    thi_flag_str = 'OBJECT( MODEL_KOOPA_FLAG, 7400, -1537, -6300, 0, 0, 0, 0, bhvKoopaFlag )'
    level_scripts[ 'bob' ].areas[ 0 ].objs.append( Obj( bob_flag_str ) )
    level_scripts[ 'thi' ].areas[ 0 ].objs.append( Obj( thi_flag_str ) )


def fix_exclamation_boxes( obj_name_to_geo_dict, geo_dict, gfx_display_dict ):
    """
    Exclamation boxes are tricky.  The different boxes are selected by geo_switch_anim_state, which is strange since they aren't animated and never switch states.  Because the geo parsing only selects the first switch state since nothing in this program is animated, it selects the wing cap box for all exclamation boxes.  We have to hardcode the different boxes into the geo_dict and then have the obj_name_to_geo_dict point to the right things.

    Lastly, the texel coordinates are actually wrong in the source code, but the unusual way the textures are loaded into memory avoid CLAMP_TO_EDGE issues.  So basically the texel coordinates to fix the wing cap box and vanish cap box are hardcoded because the source code is hardcoded.
    """
    texel_coords = [ 992, 1007, 992, 0, 0, 0, 0, 1007, 0, 0, 0, 1007, 992, 1007, 992, 0 ]

    wing_cap_box_geo = Geo( 'wing_cap_box_geo', {}, process_code=False )
    wing_cap_geo_dl = GeoDisplayList( 'LAYER_OPAQUE', 'exclamation_box_seg8_dl_08019318', util_math.identity_mat(), zbuffer=True, billboard=False )
    wing_cap_box_geo.geo_dls = [ wing_cap_geo_dl ]
    obj_name_to_geo_dict[ 'macro_box_wing_cap' ] = 'wing_cap_box_geo'
    geo_dict[ 'wing_cap_box_geo' ] = wing_cap_box_geo
    gfx_display_dict[ 'exclamation_box_seg8_dl_08019318' ][ 1 ].texel_coordinates = texel_coords.copy()

    metal_cap_box_geo = Geo( 'metal_cap_box_geo', {}, process_code=False )
    metal_cap_geo_dl = GeoDisplayList( 'LAYER_OPAQUE', 'exclamation_box_seg8_dl_08019378', util_math.identity_mat(), zbuffer=True, billboard=False )
    metal_cap_box_geo.geo_dls = [ metal_cap_geo_dl ]
    obj_name_to_geo_dict[ 'macro_box_metal_cap' ] = 'metal_cap_box_geo'
    geo_dict[ 'metal_cap_box_geo' ] = metal_cap_box_geo

    vanish_cap_box_geo = Geo( 'vanish_cap_box_geo', {}, process_code=False )
    vanish_cap_geo_dl = GeoDisplayList( 'LAYER_OPAQUE', 'exclamation_box_seg8_dl_080193D8', util_math.identity_mat(), zbuffer=True, billboard=False )
    vanish_cap_box_geo.geo_dls = [ vanish_cap_geo_dl ]
    obj_name_to_geo_dict[ 'macro_box_vanish_cap' ] = 'vanish_cap_box_geo'
    geo_dict[ 'vanish_cap_box_geo' ] = vanish_cap_box_geo
    gfx_display_dict[ 'exclamation_box_seg8_dl_080193D8' ][ 1 ].texel_coordinates = texel_coords.copy()

    exclamation_box_geo = Geo( 'exclamation_box_geo', {}, process_code=False )
    exclamation_box_geo_dl = GeoDisplayList( 'LAYER_OPAQUE', 'exclamation_box_seg8_dl_08019438', util_math.identity_mat(), zbuffer=True, billboard=False )
    exclamation_box_geo.geo_dls = [ exclamation_box_geo_dl ]
    geo_dict[ 'exclamation_box_geo' ] = exclamation_box_geo


def fix_doors( obj_name_to_geo_dict ):
    obj_name_to_geo_dict[ 'special_metal_door' ] = 'metal_door_geo'
    obj_name_to_geo_dict[ 'special_metal_door_warp' ] = 'metal_door_geo'
    obj_name_to_geo_dict[ 'special_wooden_door_warp' ] = 'wooden_door_geo'
    obj_name_to_geo_dict[ 'special_haunted_door' ] = 'wooden_door_geo'
    obj_name_to_geo_dict[ 'special_mine' ] = 'bowser_bomb_geo'
    obj_name_to_geo_dict[ 'special_0stars_door' ] = 'castle_door_0_star_geo'
    obj_name_to_geo_dict[ 'special_1star_door' ] = 'castle_door_1_star_geo'
    obj_name_to_geo_dict[ 'special_3star_door' ] = 'castle_door_3_stars_geo'
    obj_name_to_geo_dict[ 'special_castle_door' ] = 'castle_door_geo'
    obj_name_to_geo_dict[ 'special_hmc_door' ] = 'hazy_maze_door_geo'


def fix_bowser_1_yellow_spheres( level_scripts, geo_dict ):
    level_scripts[ 'bowser_1' ].geo_dict[ 'bowser_1_yellow_sphere_geo' ] = geo_dict[ 'bowser_1_yellow_sphere_geo' ]


def fix_chain_chomp( level_scripts ):
    """
    In the game's source code, this is done in a behavior function.
    """
    for each_obj in level_scripts[ 'bob' ].areas[ 0 ].macro_objs:
        if each_obj.model == 'macro_chain_chomp':
            ## Original position is 735.  Offset of +240 is added to y in behavior.
            each_obj.position[ 1 ] = 735 + 240


def fix_tox_box( level_scripts ):
    """
    In the game's source code, this is done in a behavior function.
    """
    for each_obj in level_scripts[ 'ssl' ].areas[ 0 ].objs:
        if each_obj.model == 'MODEL_SSL_TOX_BOX':
            each_obj.position[ 1 ] += 256


def fix_everything( skybox_dict, texture_dict, name_dict, model_dict, macro_dict, macro_to_geo_dict, special_dict, level_scripts, vtx_dict, gfx_dict, light_dict, gfx_display_dict, paintings_dict, movtex_dict, obj_name_to_geo_dict, geo_dict ):

    ## Note: arguments passed to functions are modified.
    fix_start_looks( level_scripts )
    fix_level_area_offsets( level_scripts )
    dedupe_level_draw_calls( level_scripts )
    remove_bbh_opaque_wall_and_ceiling( level_scripts, gfx_display_dict )
    remove_castle_basement_tile( level_scripts, gfx_display_dict )
    add_castle_lobby_light( level_scripts )
    make_castle_inside_mirror_transparent( level_scripts, gfx_display_dict )
    fix_intro_dls( gfx_display_dict )
    place_paintings( level_scripts, paintings_dict )
    fix_waterbox_colours( level_scripts )
    place_movtexs( level_scripts, movtex_dict )
    add_peach_to_castle_grounds( level_scripts )
    find_dorrie( level_scripts )
    fix_jrb_act_objs( level_scripts )
    add_treasure_chests_to_jrb( level_scripts )
    place_lll_puzzle_pieces( level_scripts )
    add_koopa_flags( level_scripts )
    fix_exclamation_boxes( obj_name_to_geo_dict, geo_dict, gfx_display_dict )
    fix_doors( obj_name_to_geo_dict )
    fix_bowser_1_yellow_spheres( level_scripts, geo_dict )
    fix_chain_chomp( level_scripts )
    fix_tox_box( level_scripts )


    return skybox_dict, texture_dict, name_dict, model_dict, macro_dict, macro_to_geo_dict, special_dict, level_scripts, vtx_dict, gfx_dict, light_dict, gfx_display_dict, paintings_dict, movtex_dict, obj_name_to_geo_dict, geo_dict



def main( mario_source_dir, mario_graphics_dir ):

    with open( mario_graphics_dir / 'm64_dicts.pickle', 'rb' ) as f:
        skybox_dict, texture_dict, name_dict = pickle.load( f )

    with open( mario_graphics_dir / 'model_dicts.pickle', 'rb' ) as f:
        model_dict, macro_dict, macro_to_geo_dict, special_dict = pickle.load( f )
    
    with open( mario_graphics_dir / 'level_scripts.pickle', 'rb' ) as f:
        level_scripts = pickle.load( f )

    with open( mario_graphics_dir / 'draw_dicts.pickle', 'rb' ) as f:
        vtx_dict, gfx_dict, light_dict, gfx_display_dict = pickle.load( f )

    with open( mario_graphics_dir / 'paintings.pickle', 'rb' ) as f:
        paintings_dict = pickle.load( f )

    with open( mario_graphics_dir / 'movtex_dict.pickle', 'rb' ) as f:
        movtex_dict = pickle.load( f )

    with open( mario_graphics_dir / 'obj_geo_dicts.pickle', 'rb' ) as f:
        obj_name_to_geo_dict, geo_dict = pickle.load( f )

    skybox_dict, texture_dict, name_dict, model_dict, macro_dict, macro_to_geo_dict, special_dict, level_scripts, vtx_dict, gfx_dict, light_dict, gfx_display_dict, paintings_dict, movtex_dict, obj_name_to_geo_dict, geo_dict = fix_everything( skybox_dict, texture_dict, name_dict, model_dict, macro_dict, macro_to_geo_dict, special_dict, level_scripts, vtx_dict, gfx_dict, light_dict, gfx_display_dict, paintings_dict, movtex_dict, obj_name_to_geo_dict, geo_dict )

    
    with open( mario_graphics_dir / 'm64_dicts.pickle', 'wb' ) as f:
        pickle.dump( [ skybox_dict, texture_dict, name_dict ], f, pickle.HIGHEST_PROTOCOL )

    with open( mario_graphics_dir / 'model_dicts.pickle' , 'wb' ) as f:
        pickle.dump( [ model_dict, macro_dict, macro_to_geo_dict, special_dict ], f, pickle.HIGHEST_PROTOCOL )

    with open( mario_graphics_dir / 'level_scripts.pickle', 'wb' ) as f:
        pickle.dump( level_scripts, f, pickle.HIGHEST_PROTOCOL )

    with open( mario_graphics_dir / 'draw_dicts.pickle', 'wb' ) as f:
        pickle.dump( [ vtx_dict, gfx_dict, light_dict, gfx_display_dict ], f, pickle.HIGHEST_PROTOCOL )

    with open( mario_graphics_dir / 'paintings.pickle', 'wb' ) as f:
        pickle.dump( paintings_dict, f, pickle.HIGHEST_PROTOCOL )

    with open( mario_graphics_dir / 'movtex_dict.pickle', 'wb' ) as f:
        pickle.dump( movtex_dict, f, pickle.HIGHEST_PROTOCOL )

    with open( mario_graphics_dir / 'obj_geo_dicts.pickle', 'wb' ) as f:
        pickle.dump( [ obj_name_to_geo_dict, geo_dict ], f, pickle.HIGHEST_PROTOCOL )

    with open( mario_graphics_dir / 'game_dicts.pickle', 'wb' ) as f:
        pickle.dump( [ level_scripts, geo_dict, gfx_display_dict, texture_dict, obj_name_to_geo_dict, special_dict ], f, pickle.HIGHEST_PROTOCOL )


    print( "Level fixes applied." )



if __name__ == "__main__":

    mario_source_dir = Path( '/home/seph/mario_source/sm64/' )
    mario_graphics_dir = Path( '/home/seph/game_practice/mario_64_graphics/' )
    main( mario_source_dir, mario_graphics_dir )

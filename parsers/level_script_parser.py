import glob
from pathlib import Path
import pickle

from util_math import scale_mat


def process_line( line ):
    """Reads a function call line.  Looks for opening and closing parentheses, and then, skipping comments, extracts the arguments to the function call."""
    if '//' in line:
        line = line[ : line.find( '//' ) ]
    start_ind = line.find( '(' ) + 1
    end_ind = line.rfind( ')' )

    ## Find all /* */ comments and remove them.
    uncommented_line = line[ start_ind : end_ind ]
    while '/*' in uncommented_line:
        comment_start = uncommented_line.find( '/*' )
        comment_end = uncommented_line.find( '*/', comment_start ) + len( '*/' )
        uncommented_line = uncommented_line[ : comment_start ] + uncommented_line[ comment_end : ]

    args = uncommented_line.split( ',' )
    ret_arr = []
    for each_arg in args:
        temp_arg = each_arg.strip()

        if '0x' in temp_arg:
            ## Try to process as a hex number
            try:
                hex_arg = int( temp_arg, 16 )
                ret_arr.append( hex_arg )
            except:
                ret_arr.append( temp_arg )

        else:
            ## Try to parse as an int, otherwise try to parse as a float with a trailing 'f'.  Otherwise, just add the string to the arg list.
            try:
                int_arg = int( temp_arg )
                ret_arr.append( int_arg )

            except:
                try:
                    if temp_arg[ -1 ] == 'f':
                        ret_arr.append( float( temp_arg[ : -1 ] ) )
                    else:
                        ret_arr.append( temp_arg )
                except:
                    ret_arr.append( temp_arg )

    if len( ret_arr ) > 1:
        return ret_arr
    elif len( ret_arr ) == 1:
        return ret_arr[ 0 ]



class LevelScript():
    def __init__( self, filepath ):
        self.filepath = filepath
        self.mario_pos = [ 1, 0, 0.0, 0.0, 0.0 ]  ## Area, yaw, x, y , z
        self.terrain_type = None
        self.background_music = None
        self.level = None
        self.level_geo = {}
        self.areas = []
        self.geo_dict = {}
        self.read_file()
        self.get_areas()
        self.set_area_level_geo()
        self.read_local_funcs()
        self.parse_macro()
        self.parse_movtex()
        self.parse_collision()
        self.parse_geo()
        

    def read_file( self ):
        self.level = self.filepath.parts[ self.filepath.parts.index( 'levels' ) + 1 ]
        with open( self.filepath, 'r' ) as f:
            self.txt = f.read()


    def get_areas( self ):
        """Creates instances of area class and appends them to self.areas.  Fills in area data.  Also sets self.mario_pos and self.level_geo, if applicable."""
        temp = [ i.strip() for i in self.txt.split( '\n' ) ]
        in_area = False
        current_area = None
        for each_line in temp:
            if each_line.strip()[ : 4 ] == 'AREA':
                in_area = True
                area_ind, area_geo = process_line( each_line )
                current_area = Area( self.level, self.filepath, area_ind )
                current_area.geo.append( area_geo )
                continue

            elif each_line.strip()[ : 8 ] == 'END_AREA':
                self.areas.append( current_area )
                in_area = False
                current_area = None
                continue

            if in_area:
                temp_line = each_line.strip()

                ## Get local function names specific to the area
                if "JUMP_LINK" in temp_line:
                    local_func = process_line( temp_line )
                    current_area.local_funcs.append( local_func )

                ## Get terrain_type specific to area
                if "TERRAIN_TYPE" in each_line:
                    current_area.terrain_type = process_line( temp_line )

                ## Get background_music specific to area
                if "SET_BACKGROUND_MUSIC" in each_line:
                    current_area.background_music = process_line( temp_line )

                ## Find any area specific objects.  These at least occur in castle_inside.
                if 'OBJECT' in each_line and 'MODEL_NONE' not in each_line and 'MACRO_OBJECTS' not in each_line:
                    current_obj = Obj( each_line )
                    if current_obj.type == 'OBJECT':
                        current_area.objs.append( current_obj )

                    elif current_obj.type == 'OBJECT_WITH_ACTS':
                        current_area.objs_with_acts.append( current_obj )

                    elif current_obj.type == 'SPECIAL_OBJECT':
                        current_area.special_objs.append( current_obj )

                    elif current_obj.type == 'MACRO_OBJECT':
                        current_area.macro_objs.append( current_obj )


            if not in_area:
                temp_line = each_line.strip()
                ## Check to see if there's any level geometry not specific to an area:
                #if "LOAD_MODEL_FROM_GEO(MODEL_LEVEL_GEOMETRY" in temp_line:
                if "LOAD_MODEL_FROM_GEO" in temp_line:
                    key, val = process_line( temp_line )
                    self.level_geo[ key ] = val

                ## Check to see if the line contains Mario's starting position.
                if "MARIO_POS" in each_line:
                    self.mario_pos = process_line( temp_line )


    def set_area_level_geo( self ):
        for each_area in self.areas:
            each_area.level_geo = self.level_geo


    def read_local_funcs( self ):
        local_funcs_to_find = {}
        for each_area in self.areas:
            for each_local_func in each_area.local_funcs:
                local_funcs_to_find[ each_local_func ] = each_area.index

        current_ind = 0
        while True:
            ## Loop to find every local function.

            ## First find the start of a local function and extract its index.
            current_ind = self.txt.find( 'static const LevelScript script_func_local_', current_ind )
            ## If there are no more local functions in the rest of the file, exit the while loop.
            if current_ind == -1:
                break
            current_ind += len( 'static const LevelScript ' )
            ## If there are no more local functions in the rest of the file, exit the while loop.
            if current_ind == -1:
                break
            bracket_ind = self.txt.find( '[', current_ind )
            local_func_name = self.txt[ current_ind : bracket_ind ]
            assert local_func_name in local_funcs_to_find.keys(), "The local function is not in any area local function lists."

            current_ind = self.txt.find( '{', current_ind )
            end_local_func_ind = self.txt.find( '};', current_ind )
            local_func_lines = [ i.strip() for i in self.txt[ current_ind : end_local_func_ind ].split( '\n' ) ]
            for each_local_line in local_func_lines:
                ## Don't bother processing objects without models.
                if 'OBJECT' in each_local_line and 'MODEL_NONE' not in each_local_line:
                    current_obj = Obj( each_local_line )
                    if current_obj.type == 'OBJECT':
                        self.areas[ local_funcs_to_find[ local_func_name ] - 1 ].objs.append( current_obj )

                    elif current_obj.type == 'OBJECT_WITH_ACTS':
                        self.areas[ local_funcs_to_find[ local_func_name ] - 1 ].objs_with_acts.append( current_obj )

                    elif current_obj.type == 'SPECIAL_OBJECT':
                        self.areas[ local_funcs_to_find[ local_func_name ] - 1 ].special_objs.append( current_obj )

                    elif current_obj.type == 'MACRO_OBJECT':
                        self.areas[ local_funcs_to_find[ local_func_name ] - 1 ].macro_objs.append( current_obj )

                    else:
                        raise ValueError( "Unknown object type." )


    def parse_geo( self ):
        for each_area in self.areas:
            for each_geo_path in each_area.filepath.glob( '**/geo.inc.c' ):
                with open( each_geo_path, 'r' ) as f:
                    geo_txt = f.read()

                ## Find all GeoLayouts in the file.
                current_ind = 0
                while True:
                    current_ind = geo_txt.find( 'GeoLayout ', current_ind )
                    if current_ind == -1:
                        break
                    current_ind += len( 'GeoLayout ' )
                    name_end_ind = geo_txt.find( '[', current_ind )
                    current_geo_name = geo_txt[ current_ind : name_end_ind ]

                    current_ind = geo_txt.find( '{', current_ind ) + len( '{' )
                    end_ind = geo_txt.find( '};', current_ind )
                    current_geo_code = geo_txt[ current_ind : end_ind ]
                    self.geo_dict[ current_geo_name ] = LevelGeo( current_geo_name, current_geo_code )

                ## Read through the file again and resolve geo references.
                current_ind = 0
                while True:
                    current_ind = geo_txt.find( 'GeoLayout ', current_ind )
                    if current_ind == -1:
                        break
                    current_ind += len( 'GeoLayout ' )
                    name_end_ind = geo_txt.find( '[', current_ind )
                    current_geo_name = geo_txt[ current_ind : name_end_ind ]

                    current_ind = geo_txt.find( '{', current_ind ) + len( '{' )
                    end_ind = geo_txt.find( '};', current_ind )
                    current_geo_code = geo_txt[ current_ind : end_ind ]

                    ## Resolve geo references.
                    if 'GEO_BRANCH' in current_geo_code:
                        current_geo_lines = [ i.strip() for i in geo_txt.split( '\n' ) ]
                        geo_names_to_resolve = []

                        for each_line in current_geo_lines:
                            if 'GEO_BRANCH' in each_line:
                                _, geo_name = process_line( each_line )
                                geo_names_to_resolve.append( geo_name )


                        ## Now we have the names and we can iterate through them and update current_geo_name.
                        for each_name in geo_names_to_resolve:
                            self.geo_dict[ current_geo_name ].shadows += self.geo_dict[ each_name ].shadows
                            self.geo_dict[ current_geo_name ].geo_dls += self.geo_dict[ each_name ].geo_dls



        ## Need to process level_geo that is in the root of the level folder.
        root_level_geo = [ each_filepath for each_filepath in self.filepath.parent.glob( '**/geo.inc.c' ) if 'areas' not in each_filepath.parent.parts ]
        for each_geo_path in root_level_geo:
            with open( each_geo_path, 'r' ) as f:
                geo_txt = f.read()

            ## Find all GeoLayouts in the file.
            current_ind = 0
            while True:
                current_ind = geo_txt.find( 'GeoLayout ', current_ind )
                if current_ind == -1:
                    break
                current_ind += len( 'GeoLayout ' )
                name_end_ind = geo_txt.find( '[', current_ind )
                current_geo_name = geo_txt[ current_ind : name_end_ind ]

                current_ind = geo_txt.find( '{', current_ind ) + len( '{' )
                end_ind = geo_txt.find( '};', current_ind )
                current_geo_code = geo_txt[ current_ind : end_ind ]
                self.geo_dict[ current_geo_name ] = LevelGeo( current_geo_name, current_geo_code )



    def parse_collision( self ):
        for each_area in self.areas:
            for each_collision_path in each_area.filepath.glob( '**/collision.inc.c' ):
                with open( each_collision_path, 'r' ) as f:
                    collision_txt = f.read()

                collision_lines = [ i.strip() for i in collision_txt.split( '\n' ) ]
                for each_line in collision_lines:
                    if 'OBJECT' in each_line:
                        each_area.special_objs.append( Obj( each_line ) )

                    elif 'COL_WATER_BOX' in each_line and 'COL_WATER_BOX_INIT' not in each_line:
                        ## We need to match up waterboxes that are in areas[].movtex with the current line.
                        ind, x1, z1, x2, z2, y = process_line( each_line )
                        for each_water_box in each_area.movtex:
                            if isinstance( each_water_box, WaterBox ):
                                if each_water_box.index == ind:
                                    each_water_box.set_height( y )

    
    def parse_macro( self ):
        for each_area in self.areas:
            for each_macro_path in each_area.filepath.glob( '**/macro.inc.c' ):
                with open( each_macro_path, 'r' ) as f:
                    macro_txt = f.read()

                macro_lines = [ i.strip() for i in macro_txt.split( '\n' ) ]
                for each_line in macro_lines:
                    if 'OBJECT' in each_line and 'MACRO_OBJECT_END' not in each_line:
                        each_area.macro_objs.append( Obj( each_line ) )


    def parse_movtex( self ):
        for each_area in self.areas:
            for each_movtex_path in each_area.filepath.glob( '**/movtext.inc.c' ):
                with open( each_movtex_path, 'r' ) as f:
                    movtex_txt = f.read()

                ## Find each MovtexQuadCollection and parse out the quads from it.
                current_ind = 0
                while True:
                    current_ind = movtex_txt.find( '{', movtex_txt.find( 'MovtexQuadCollection', current_ind ) )
                    if current_ind != -1:
                        ## Then there are waterboxes in the file
                        current_ind += 1
                        end_ind = movtex_txt.find( '};', current_ind )

                        quad_names = []
                        while True:
                            current_ind = movtex_txt.find( '{', current_ind ) + 1
                            entry_end_ind = movtex_txt.find( '}', current_ind )
                            quad_ind = int( movtex_txt[ current_ind : entry_end_ind ].split( ',' )[ 0 ].strip() )
                            quad_name = movtex_txt[ current_ind : entry_end_ind ].split( ',' )[ 1 ].strip()
                            if quad_name == 'NULL':
                                break
                            else:
                                quad_names.append( [ quad_ind, quad_name ] )


                        ## Find opening and closing curly braces and look to see if a waterbox is contained inside:
                        for each_quad in quad_names:
                            quad_ind = movtex_txt.find( each_quad[ 1 ] )
                            quad_end_ind = movtex_txt.find( '};', quad_ind )
                            ## Parse each water_box from the single water data.
                            each_area.movtex += self.parse_waterbox( movtex_txt[ quad_ind : quad_end_ind ], each_quad[ 0 ] )

                    elif current_ind == -1:
                        break


    def parse_waterbox( self, code_lines, ind ):
        waterbox_texture_dict = { 'TEXTURE_WATER' : 'texture_waterbox_water', 'TEXTURE_MIST' : 'texture_waterbox_mist', 'TEXTURE_JRB_WATER' : 'texture_waterbox_jrb_water', 'TEXTURE_UNK_WATER' : 'texture_waterbox_unknown_water', 'TEXTURE_LAVA' : 'texture_waterbox_lava', 'TEX_QUICKSAND_SSL' : 'ssl_quicksand', 'TEX_PYRAMID_SAND_SSL' : 'ssl_pyramid_sand', 'TEX_YELLOW_TRI_TTC' : 'ttc_yellow_triangle' }
        lines = [ i.strip() for i in code_lines.split( '\n' ) ]
        for line_ind, each_line in enumerate( lines ):
            if 'MOV_TEX_INIT_LOAD' in each_line:
                num_waterboxes = process_line( each_line )
                waterbox_start_ind = line_ind + 1
                break

        ret_waterboxes = []
        for i in range( num_waterboxes ):
            curr_waterbox = WaterBox( ind=ind )
            curr_waterbox.rot_speed = process_line( lines[ waterbox_start_ind ] )
            curr_waterbox.scale = process_line( lines[ waterbox_start_ind + 1 ] )
            x, z = process_line( lines[ waterbox_start_ind + 2 ] )
            curr_waterbox.vert1 = [ x, 0, z ]
            x, z = process_line( lines[ waterbox_start_ind + 3 ] )
            curr_waterbox.vert2 = [ x, 0, z ]
            x, z = process_line( lines[ waterbox_start_ind + 4 ] )
            curr_waterbox.vert3 = [ x, 0, z ]
            x, z = process_line( lines[ waterbox_start_ind + 5 ] )
            curr_waterbox.vert4 = [ x, 0, z ]
            direction = process_line( lines[ waterbox_start_ind + 6 ] )
            if direction == 'ROTATE_COUNTER_CLOCKWISE':
                curr_waterbox.rotation_direction = 1
            elif direction == 'ROTATE_CLOCKWISE':
                curr_waterbox.rotation_direction = 0
            curr_waterbox.alpha = process_line( lines[ waterbox_start_ind + 7 ] )
            curr_waterbox.colour = [ 255, 255, 255, curr_waterbox.alpha ]
            curr_waterbox.texture = waterbox_texture_dict[ process_line( lines[ waterbox_start_ind + 8 ] ) ]
            assert 'MOV_TEX_END' in lines[ waterbox_start_ind + 9 ], "Waterbox parsing failed."
            ret_waterboxes.append( curr_waterbox )
            waterbox_start_ind += 10

        return ret_waterboxes


    def process_line( self, line ):
        """Reads a function call line.  Looks for opening and closing parentheses, and then, skipping comments, extracts the arguments to the function call."""
        start_ind = line.find( '(' ) + 1
        end_ind = line.rfind( ')' )
        args = line[ start_ind : end_ind ].split( ',' )
        ret_arr = []
        for each_arg in args:
            temp_arg = each_arg.strip()
            while '/*' in temp_arg:
                comment_ind = temp_arg.find( '/*' )
                end_comment_ind = temp_arg.find( '*/', comment_ind + 1 ) + len( '*/' )
                temp_arg = temp_arg[ : comment_ind ].strip() + temp_arg[ end_comment_ind : ].strip()


            if '0x' in temp_arg:
                ## Try to process as a hex number
                try:
                    hex_arg = int( temp_arg, 16 )
                    ret_arr.append( hex_arg )
                except:
                    pass

            else:
                ## Try to parse as an int, otherwise just add the string to the arg list.
                try:
                    int_arg = int( temp_arg )
                    ret_arr.append( int_arg )

                except:
                    ret_arr.append( temp_arg )

        if len( ret_arr ) > 1:
            return ret_arr
        elif len( ret_arr ) == 1:
            return ret_arr[ 0 ]


class LevelGeo():
    def __init__( self, name, code ):
        self.name = name
        self.shadows = []
        self.geo_dls = []
        self.process_code( code )


    def process_code( self, code ):
        ## Because level geo files are much simpler than object geo files, we can avoid implementing a parser for all kinds of graph display nodes.  We can also cheat a little bit on GEO_SCALE and GEO_RENDER_RANGE because of how simple the few uses are in level geo.
        current_scale = 1.0
        geo_lines = [ i.strip() for i in code.split( '\n' ) ]
        geo_render_range_ignore = False
        geo_render_range_open_node = False
        for each_line in geo_lines:
            if 'GEO_DISPLAY_LIST' in each_line:
                if not geo_render_range_open_node:
                    current_geo_display_list = LevelGeoDisplayList( each_line, scale=current_scale )
                    if current_geo_display_list.dl_name != 'NULL':
                        self.geo_dls.append( LevelGeoDisplayList( each_line, scale=current_scale ) )

            elif 'GEO_SCALE' in each_line:
                layer, scale = process_line( each_line )
                current_scale *= ( scale / 65536 )

            elif 'GEO_ANIMATED_PART' in each_line:
                current_geo_display_list = LevelGeoDisplayList( each_line, scale=current_scale )
                if current_geo_display_list.dl_name != 'NULL':
                    self.geo_dls.append( LevelGeoDisplayList( each_line, scale=current_scale ) )

            elif 'GEO_BILLBOARD' in each_line:
                ## Required for trees to work.
                pass

            elif 'GEO_RENDER_RANGE' in each_line:
                near, far = process_line( each_line )
                if near > 0:
                    geo_render_range_ignore = True

            elif 'GEO_OPEN_NODE' in each_line:
                if geo_render_range_ignore == True:
                    geo_render_range_open_node = True

            elif 'GEO_CLOSE_NODE' in each_line:
                if geo_render_range_open_node == True:
                    geo_render_range_ignore = False
                    geo_render_range_open_node = False




class LevelGeoDisplayList():
    def __init__( self, line, scale=1.0, zbuffer=True, billboard=False ):
        self.scale = scale
        self.transformation = scale_mat( scale )
        self.zbuffer = zbuffer
        self.billboard = billboard
        self.layer = None
        self.dl_name = None
        self.parse_cases( line )

    def parse_cases( self, code_line ):
        ## GEO_ANIMATED_PART(layer, x, y, z, displayList)
        ## Note, for level geometry, this is ONLY used for the castle_grounds flags.
        ## Not sure if this is supposed to accumulate between nodes or not.
        if 'GEO_ANIMATED_PART' in code_line:
            self.layer, x, y, z, self.dl_name = process_line( code_line )

        elif 'GEO_DISPLAY_LIST' in code_line:
            self.layer, self.dl_name = process_line( code_line )



class Area():
    def __init__( self, level, level_filepath, area_index ):
        self.level = level
        self.index = area_index
        self.filepath = level_filepath.parent / 'areas' / str( self.index )
        self.offset = [ 0, 0, 0 ] ## x, y, z offset of the entire area
        self.paintings = []
        self.local_funcs = []
        self.terrain_type = None
        self.background_music = None
        self.macro_objs = []
        self.objs = []
        self.objs_with_acts = []
        self.special_objs = []
        self.movtex = []
        self.geo = []
        self.level_geo = {}



class Obj():
    """Takes in a line of code with 'OBJECT' in the line.  Parses the line and extracts relevant object information."""
    def __init__( self, code_line ):
        self.model = None
        self.angle = None
        self.position = None
        self.type = None
        ## behParam and beh don't exist for all objects.
        self.behParam = None
        self.beh = None
        ## Only for OBJECTS_WITH_ACTS
        self.acts = None

        self.process_obj( code_line )
        self.process_acts()


    def process_obj( self, code_line ):
        ## There are 7 different kinds of objects to process:
        #define OBJECT_WITH_ACTS(model, posX, posY, posZ, angleX, angleY, angleZ, behParam, beh, acts) \
        #define OBJECT(model, posX, posY, posZ, angleX, angleY, angleZ, behParam, beh) \
        #define MACRO_OBJECT_WITH_BEH_PARAM(preset, yaw, posX, posY, posZ, behParam) \
        #define MACRO_OBJECT(preset, yaw, posX, posY, posZ) \
        #define SPECIAL_OBJECT(preset, posX, posY, posZ) \
        #define SPECIAL_OBJECT_WITH_YAW(preset, posX, posY, posZ, yaw) \
        #define SPECIAL_OBJECT_WITH_YAW_AND_PARAM(preset, posX, posY, posZ, yaw, param) \
        if 'OBJECT_WITH_ACTS(' in code_line:
            model, posX, posY, posZ, angleX, angleY, angleZ, behParam, beh, acts = process_line( code_line )
            self.angle = [ angleX, angleY, angleZ ]
            self.type = 'OBJECT_WITH_ACTS'
            self.behParam = behParam
            self.beh = beh
            self.acts = acts
            self.model = model

        elif 'MACRO_OBJECT_WITH_BEH_PARAM(' in code_line:
            preset, yaw, posX, posY, posZ, behParam = process_line( code_line )
            self.type = 'MACRO_OBJECT'
            self.angle = [ 0, yaw, 0 ]
            self.model = preset
            self.behParam = behParam

        elif 'MACRO_OBJECT(' in code_line:
            preset, yaw, posX, posY, posZ = process_line( code_line )
            self.type = 'MACRO_OBJECT'
            self.angle = [ 0, yaw, 0 ]
            self.model = preset

        elif 'SPECIAL_OBJECT_WITH_YAW_AND_PARAM(' in code_line:
            preset, posX, posY, posZ, yaw, param = process_line( code_line )
            self.type = 'SPECIAL_OBJECT'
            ## Oddly, yaw for special objects seems to be a u8.  So we have to divide by 256 and multiply by 360.
            self.angle = [ 0, yaw * 360 / 256, 0 ]
            self.model = preset
            self.behParam = param

        elif 'SPECIAL_OBJECT_WITH_YAW(' in code_line:
            preset, posX, posY, posZ, yaw = process_line( code_line )
            self.type = 'SPECIAL_OBJECT'
            ## Oddly, yaw for special objects seems to be a u8.  So we have to divide by 256 and multiply by 360.
            self.angle = [ 0, yaw * 360 / 256, 0 ]
            self.model = preset

        elif 'SPECIAL_OBJECT(' in code_line:
            preset, posX, posY, posZ = process_line( code_line )
            self.type = 'SPECIAL_OBJECT'
            self.angle = [ 0, 0, 0 ]
            self.model = preset

        ## Some objects are formatted to line up with 'OBJECT_WITH_ACTS'
        elif 'OBJECT(' in code_line or 'OBJECT          (' in code_line:
            model, posX, posY, posZ, angleX, angleY, angleZ, behParam, beh = process_line( code_line )
            self.type = 'OBJECT'
            self.angle = [ angleX, angleY, angleZ ]
            self.model = model
            self.behParam = behParam
            self.beh = beh

        else:
            print( code_line )
            raise ValueError( "The line of code does not seem to have a properly formatted object in it." )


        self.position = [ posX, posY, posZ ]


    def process_acts( self ):
        if self.type == 'OBJECT_WITH_ACTS':
            acts = self.acts.replace( 'ACT_', '' )
            self.acts = [ each_act.strip() for each_act in acts.split( '|' ) ]



class WaterBox():
    def __init__( self, code_lines=None, ind=None ):
        self.index = ind
        self.vert1 = None
        self.vert2 = None
        self.vert3 = None
        self.vert4 = None
        self.rot_speed = None
        self.y = None
        self.rotation_direction = None
        self.scale = None
        self.alpha = None
        self.colour = None
        self.texture = None
        if code_lines is not None:
            self.process_lines( code_lines )


    def set_height( self, y ):
        self.y = y
        self.vert1[ 1 ] = self.y
        self.vert2[ 1 ] = self.y
        self.vert3[ 1 ] = self.y
        self.vert4[ 1 ] = self.y





############
### MAIN ###
############


def main( mario_source_dir, mario_graphics_dir ):

    level_dir = mario_source_dir / 'levels'
    
    level_script_paths = [ i for i in level_dir.glob(  '**/script.c' ) ]
    
    ## Remove level scripts for the intro, ending, and menu
    for i in level_script_paths:
        if 'ending' in i.parts or 'intro' in i.parts or 'menu' in i.parts:
            level_script_paths.remove( i )
    
    ## There are now 30 level scripts.
    
    level_scripts = {}
    for each_path in level_script_paths:
        name_ind = each_path.parts.index( 'levels' ) + 1
        name = each_path.parts[ name_ind ]
        level_scripts[ name ]= LevelScript( each_path )

    with open( mario_graphics_dir / 'level_scripts.pickle', 'wb' ) as f:
        pickle.dump( level_scripts, f, pickle.HIGHEST_PROTOCOL )

    print( "Wrote level_scripts to file." )


if __name__ == "__main__":
    mario_source_dir = Path( "/home/seph/mario_source/sm64/" )
    mario_graphics_dir = Path( '/home/seph/game_practice/mario_64_graphics/' )
    main( mario_source_dir, mario_graphics_dir )

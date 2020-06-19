from pathlib import Path
import pickle
import numpy as np

from .level_script_parser import process_line
from util_math import identity_mat, scale_mat, translate_mat, rotate_around_x, rotate_around_y, rotate_around_z


def s16(x):
    x = int(x)
    return (x & 0xFFFF) - (x << 1 & 0x10000)


def remove_if_def( source ):
    if '#ifdef' in source or '#ifndef' in source:
        source_lines = source.splitlines()
        ret_lines = []
        include_line = True
        important_words = [ '#ifdef', '#ifndef', '#else', '#endif' ]
        for each_line in source_lines:
            important_word = False
            for each_important_word in important_words:
                if each_important_word in each_line:
                    important_word = True

            if important_word == False:
                if include_line:
                    ret_lines.append( each_line )

            elif '#ifdef' in each_line:
                if 'VERSION_US' in each_line:
                    include_line = True
                else:
                    include_line = False

            elif '#ifndef' in each_line:
                if 'VERSION_US' in each_line:
                    include_line = False
                else:
                    include_line = True

            elif '#else' in each_line:
                if include_line == True:
                    include_line = False
                else:
                    include_line = True

            elif '#endif' in each_line:
                include_line = True


        return '\n'.join( ret_lines )
    else:
        return source


def find_equal_in_c_source( source ):
    ind = 0
    while ind < len( source ):
        if source[ ind : ind + 2 ] == '//':
            ## Avoid comments that go till the end of the line.
            if source.find( '\n', ind ) != -1:
                ind = source.find( '\n', ind )
            else:
                return -1

        elif source[ ind : ind + 2 ] == '/*':
            ## Avoid start/end comments.
            if source.find( '*/', ind ) != -1:
                ind = source.find( '*/', ind )
            else:
                return -1

        elif source[ ind ] == '=':
            equal_ind = ind
            break

        if ind == len( source ) - 1:
            return -1

        ind += 1

    return equal_ind


def get_name( source ):
    equal_ind = find_equal_in_c_source( source )

    ind = equal_ind

    while ind > 0:
        if source[ ind ] == '\n' or ind == 0:
            start_ind = ind
            break

        ind -= 1

    def_line = source[ start_ind : equal_ind ]
    def_words = def_line.split()

    name = def_words[ -1 ]
    name = name.replace( '[', '' )
    name = name.replace( ']', '' )
    name = name.replace( '*', '' )

    return name


def read_struct_entries( source ):
    equal_ind = find_equal_in_c_source( source )
    entries = source[ equal_ind : ]
    entries = entries.replace( '\n', '' )
    entries = entries.replace( '{', '(' )
    entries = entries.replace( '}', ')' )
    args = [ i for i in process_line( entries ) if i != '' and i != 'NULL' ]
    for i in range( len( args ) ):
        if type( args[ i ] ) == str and '&' in args[ i ]:
            args[ i ] = args[ i ].replace( '&', '' )
    return args




class Geo():
    def __init__( self, name, geo_source_dict, animation=None, process_code=True ):
        self.name = name
        self.animation = animation
        self.geo_dls = []
        if process_code:
            self.geo_dls = self.process_code( name, geo_source_dict, animation=animation )


    def process_code( self, name, geo_source_dict, parent_node=None, animation=None ):
        ## GEO_ZBUFFER( TRUE/FALSE )
        ## GEO_TRANSLATE_ROTATE(layer, tx, ty, tz, rx, ry, rz)
        ## GEO_TRANSLATE_ROTATE_WITH_DL(layer, tx, ty, tz, rx, ry, rz, displayList)
        ## GEO_TRANSLATE_NODE(layer, ux, uy, uz)
        ## GEO_ROTATION_NODE(layer, ux, uy, uz)
        ## GEO_ANIMATED_PART(layer, x, y, z, displayList)
        ## GEO_DISPLAY_LIST(layer, displayList)
        ## GEO_SHADOW(type, solidity, scale)
        ## GEO_ASM(param, function)
        ## GEO_HELD_OBJECT(param, ux, uy, uz, nodeFunc)
        ## GEO_SCALE(layer, scale)
        ## TODO: parse GEO_NODE_START??

        ## The end goal of all of this is just to get a displayList with properly translated/rotated/scaled vertices and to draw it in the correct order according to layer.
        dl_list = []
        node_stack = [ parent_node or GeoNode() ]
        current_node = node_stack[ -1 ].copy()
        current_joint = 0
        switch_seen = 0
        switch_max = 0
        code = geo_source_dict[ name ]
        #print( code )
        geo_lines = [ i.strip() for i in code.split( '\n' ) ]
        for each_line in geo_lines:

            if 'GEO_DISPLAY_LIST' in each_line:
                ## Use node_stack[ -1 ] or current_node??  In almost every case, they should be the same.
                if switch_max == 0 or ( switch_max > 0 and switch_seen == 0 ):
                    layer, dl_name = process_line( each_line )

                    if dl_name != 'NULL':
                        if node_stack[ -1 ].render_range == True:
                            if node_stack[ -1 ].render_range_near == True:
                                dl_list.append( GeoDisplayList( layer, dl_name, node_stack[ -1 ].transformation.copy(), node_stack[ -1 ].zbuffer, node_stack[ -1 ].billboard ) )

                        else:
                            if node_stack[ -1 ].billboard == True:
                                ## Billboarded display lists are not scaled, so multiply the transformation matrix by a scale matrix of 1/scale to unscale.
                                if node_stack[ -1 ].scale != 0:
                                    temp_transformation = scale_mat( 1 / node_stack[ -1 ].scale ) @ node_stack[ -1 ].transformation.copy()
                                else: temp_transformation = node_stack[ -1 ].transformation.copy()
                                dl_list.append( GeoDisplayList( layer, dl_name, temp_transformation, node_stack[ -1 ].zbuffer, node_stack[ -1 ].billboard ) )
                            else:
                                dl_list.append( GeoDisplayList( layer, dl_name, node_stack[ -1 ].transformation, node_stack[ -1 ].zbuffer, node_stack[ -1 ].billboard ) )

                if switch_max > 0:
                    switch_seen += 1

                if switch_max == switch_seen:
                    switch_max = 0
                    switch_seen = 0


            elif 'GEO_ANIMATED_PART' in each_line:
                layer, tx, ty, tz, dl_name = process_line( each_line )

                if switch_max == 0 or ( switch_max > 0 and switch_seen == 0 ):
                    if current_node.render_range == True:
                        if current_node.render_range_near == True:
                            animated_transition_mat = animation.calculate_transition_mat( tx, ty, tz, current_joint )
                            current_node = node_stack[ -1 ].copy()
                            current_node.transformation = animated_transition_mat @ current_node.transformation
                            current_joint += 1
                            
                            if dl_name != 'NULL':
                                dl_list.append( GeoDisplayList( layer, dl_name, current_node.transformation, current_node.zbuffer, current_node.billboard ) )

                    else:
                        animated_transition_mat = animation.calculate_transition_mat( tx, ty, tz, current_joint )
                        current_node = node_stack[ -1 ].copy()
                        current_node.transformation = animated_transition_mat @ current_node.transformation
                        current_joint += 1
                        if dl_name != 'NULL':
                            dl_list.append( GeoDisplayList( layer, dl_name, current_node.transformation, current_node.zbuffer, current_node.billboard ) )

                if switch_max > 0:
                    switch_seen += 1

                if switch_max == switch_seen:
                    switch_max = 0
                    switch_seen = 0


            elif 'GEO_OPEN_NODE' in each_line:
                node_stack.append( current_node )
                current_node = node_stack[ -1 ].copy()

            elif 'GEO_CLOSE_NODE' in each_line:
                if self.name != 'bowser_geo':
                    if node_stack:
                        current_node = node_stack.pop()

                else:
                    ## Intentionally parse bowser_geo wrong because it somehow fixes his head despite not doing the GEO_ASM function.  Ugly hack...
                    if node_stack:
                        node_stack.pop()
                        if node_stack:
                            current_node = node_stack[ -1 ].copy()

            elif 'GEO_ZBUFFER' in each_line:
                zbuffer = process_line( each_line )
                current_node.zbuffer = bool( zbuffer )

            elif 'GEO_RENDER_RANGE' in each_line:
                near, far = process_line( each_line )
                current_node.render_range = True
                if near < 0:
                    current_node.render_range_near = True
                else:
                    current_node.render_range_near = False

            elif 'GEO_SWITCH_CASE' in each_line:
                ## GEO_SWITCH_CASE(count, function)
                count, function = process_line( each_line )
                if function != 'geo_switch_area':
                    switch_max = count
                    switch_seen = 0

            elif 'GEO_BRANCH' in each_line:
                if 'GEO_BRANCH_AND_LINK' in each_line:
                    branch_name = process_line( each_line )
                else:
                    _, branch_name = process_line( each_line )

                if branch_name != 'NULL':
                    if switch_max == 0:
                        dl_list += self.process_code( branch_name, geo_source_dict, parent_node=current_node, animation=animation )
    
                    else:
                        if switch_seen == 0:
                            dl_list += self.process_code( branch_name, geo_source_dict, parent_node=current_node, animation=animation )
                            switch_seen += 1
    
                if switch_seen == switch_max:
                    switch_seen = 0
                    switch_max = 0

            elif 'GEO_TRANSLATE_ROTATE_WITH_DL' in each_line:
                ## GEO_TRANSLATE_ROTATE_WITH_DL(layer, tx, ty, tz, rx, ry, rz, displayList)
                layer, tx, ty, tz, rx, ry, rz, dl_name = process_line( each_line )
                if switch_max == 0 or ( switch_max > 0 and switch_seen == 0 ):
                    translation_matrix = translate_mat( tx, ty, tz )
                    rot_x = rotate_around_x( rx )
                    rot_y = rotate_around_y( ry )
                    rot_z = rotate_around_z( rz )
                    rotation_matrix = rot_z @ rot_x @ rot_y
                    current_node.transformation = current_node.transformation @ rotation_matrix @ translation_matrix
                    if dl_name != 'NULL':
                        if current_node.render_range == True:
                            if current_node.render_range_near == True:
                                dl_list.append( GeoDisplayList( layer, dl_name, current_node.transformation, current_node.zbuffer, current_node.billboard ) )

                        else:
                            dl_list.append( GeoDisplayList( layer, dl_name, current_node.transformation, current_node.zbuffer, current_node.billboard ) )

                if switch_max > 0:
                    switch_seen += 1

                if switch_max == switch_seen:
                    switch_max = 0
                    switch_seen = 0

            elif 'GEO_NODE_START' in each_line:
                if switch_max > 0:
                    pass
                    #print( self.name )

            elif 'GEO_TRANSLATE_ROTATE' in each_line:
                ## GEO_TRANSLATE_ROTATE(layer, tx, ty, tz, rx, ry, rz)
                layer, tx, ty, rz, rx, ry, rz = process_line( each_line )
                translation_matrix = translate_mat( tx, ty, tz )
                rot_x = rotate_around_x( rx )
                rot_y = rotate_around_y( ry )
                rot_z = rotate_around_z( rz )
                rotation_matrix = rot_z @ rot_x @ rot_y
                current_node.transformation = current_node.transformation @ rotation_matrix @ translation_matrix

            elif 'GEO_TRANSLATE_NODE' in each_line:
                ## GEO_TRANSLATE_NODE(layer, ux, uy, uz)
                layer, tx, ty, tz = process_line( each_line )
                translation_matrix = translate_mat( tx, ty, tz )
                #current_node.transformation = current_node.transformation @ translation_matrix
                current_node.transformation = translation_matrix @ current_node.transformation

            elif 'GEO_ROTATION_NODE' in each_line:
                ## GEO_ROTATION_NODE(layer, ux, uy, uz)
                layer, rx, ry, rz = process_line( each_line )
                rot_x = rotate_around_x( rx )
                rot_y = rotate_around_y( ry )
                rot_z = rotate_around_z( rz )
                rotation_matrix = rot_z @ rot_x @ rot_y
                current_node.transformation = current_node.transformation @ rotation_matrix

            elif 'GEO_BILLBOARD' in each_line:
                current_node.billboard = True

            elif 'GEO_SCALE' in each_line:
                layer, scale = process_line( each_line )
                scale = scale / 65536
                current_node.scale = scale
                scale_transformation = scale_mat( scale )
                #pass
                #current_node.transformation = current_node.transformation @ scale_transformation
                current_node.transformation = scale_transformation @ current_node.transformation

            elif 'GEO_ASM' in each_line:
                pass

            elif 'GEO_SHADOW' in each_line:
                pass

            elif 'GEO_HELD_OBJECT' in each_line:
                ## This is only used in Mario's animations.
                pass

            else:
                pass


        return dl_list





class GeoNode():
    def __init__( self, transformation=None, zbuffer=True, billboard=False, render_range=False, render_range_near=None, scale=1.0, switch_state=None ):
        if transformation is not None:
            self.transformation = transformation.copy()
        else:
            self.transformation = identity_mat()
        self.zbuffer = zbuffer
        self.billboard = billboard
        self.render_range = render_range
        self.render_range_near = render_range_near
        self.scale = scale
        self.switch_state = switch_state

    def copy( self ):
        copy_obj = GeoNode( transformation=self.transformation, zbuffer=self.zbuffer, billboard=self.billboard, render_range=self.render_range, render_range_near=self.render_range_near, scale=self.scale, switch_state=self.switch_state )
        return copy_obj


class GeoDisplayList():
    def __init__( self, layer, dl_name, transformation, zbuffer=True, billboard=False ):
        ## Transformation matrix contains scale, rotation, and translation information.
        self.transformation = transformation.copy()
        self.zbuffer = zbuffer
        self.billboard = billboard
        self.layer = layer
        self.dl_name = dl_name


class Animation():
    def __init__( self, anim_name, anim_source_dict=None ):
        self.name = anim_name
        self.frame = 0
        self.joint_type = None
        self.flags = None
        self.unk02 = None
        self.unk04 = None
        self.unk06 = None
        self.unk08 = None
        self.numparts = None
        self.index_arr_name = None
        self.index_arr = None
        self.index_arr_index = None
        self.value_arr_name = None
        self.value_arr = None
        self.length = None
        if anim_source_dict:
            self.parse_and_init( anim_source_dict )

    def parse_and_init( self, anim_source_dict ):
        self.flags, self.unk02, self.unk04, self.unk06, self.unk08, _, self.value_arr_name, self.index_arr_name, self.length = read_struct_entries( anim_source_dict[ self.name ] )
        self.index_arr = read_struct_entries( anim_source_dict[ self.index_arr_name ] )
        ## Some animvalue arrays need to be converted from u16 to s16.  We look at the string to see if there are any 0x in it.
        value_arr_str = anim_source_dict[ self.value_arr_name ]
        need_to_convert = '0x' in value_arr_str[ find_equal_in_c_source( value_arr_str ) : ]
        self.value_arr = read_struct_entries( anim_source_dict[ self.value_arr_name ] )
        if need_to_convert:
            self.value_arr = [ s16( x ) for x in self.value_arr ]
        self.numparts = len( self.index_arr ) // 6 - 1
        self.set_joint_type()

    def set_joint_type( self ):
        if self.flags & 0x0008:
            self.joint_type = 2
        elif self.flags & 0x0010:
            self.joint_type = 3
        elif self.flags & 0x0040:
            self.joint_type = 4
        else:
            self.joint_type = 1


    def joint_read( self ):
        try:
            cap = self.index_arr[ self.index_arr_index ]
            self.index_arr_index += 1
            index = self.index_arr[ self.index_arr_index ]
            self.index_arr_index += 1
            if self.frame < cap:
                index += self.frame
            else:
                index += cap - 1
            return self.value_arr[ index ]
        except:
            return 0

    def convert_to_degs( self, val ):
        """
        Converts an s16 to degrees with a minimum output of -180 and a maximum output of 180 degrees.
        """
        return val * 180 / 32768


    def calculate_transition_mat( self, tx, ty, tz, joint_num ):
        trans_x, trans_y, trans_z = tx, ty, tz
        if joint_num == 0:
            self.index_arr_index = 0

            if self.joint_type == 1:
                trans_x += self.joint_read()
                trans_y += self.joint_read()
                trans_z += self.joint_read()

            elif self.joint_type == 2:
                self.index_arr_index += 2
                trans_y += self.joint_read()
                self.index_arr_index += 2

            elif self.joint_type == 3:
                trans_x += self.joint_read()
                self.index_arr_index += 2
                trans_z += self.joint_read()

            elif self.joint_type == 4:
                self.index_arr_index += 6

        rx = self.convert_to_degs( self.joint_read() )
        ry = self.convert_to_degs( self.joint_read() )
        rz = self.convert_to_degs( self.joint_read() )
        translate_matrix = translate_mat( trans_x, trans_y, trans_z )
        rot_x_matrix = rotate_around_x( rx )
        rot_y_matrix = rotate_around_y( ry )
        rot_z_matrix = rotate_around_z( rz )
        return rot_x_matrix @ rot_y_matrix @ rot_z_matrix @ translate_matrix



############
### MAIN ###
############


def main( mario_source_dir, mario_graphics_dir ):

    ## Don't deal with Mario animations since they're stored in a different way.
    mario_actor_path = mario_source_dir / 'actors' / 'mario'
    geo_filepaths = [ i for i in mario_source_dir.glob( '**/geo.inc.c' ) if i.parent != mario_actor_path ]
    
    layer_dict = { 'LAYER_FORCE' : 0, 'LAYER_OPAQUE' : 1, 'LAYER_OPAQUE_DECAL' : 2, 'LAYER_OPAQUE_INTER' : 3, 'LAYER_ALPHA' : 4, 'LAYER_TRANSPARENT' : 5, 'LAYER_TRANSPARENT_DECAL' : 6, 'LAYER_TRANSPARENT_INTER' : 7 }
    
    ## Chooses which animation in the animation list will be used.
    animated_objects_dict = { \
    '11': 0, 
    'amp': 0, 
    'bird': 0, 
    'blargg': 0, 
    'blue_fish': 0, 
    'bobomb': 0, 
    'bookend': 0, 
    'bowser': 3, 
    'bowser_key': 0, 
    'bub': 0, 
    'bully': 0, 
    'butterfly': 0, 
    'chain_chomp': 0, 
    'chair': 0, 
    'chillychief': 0, 
    'chuckya': 0, 
    'clam_shell': 0, 
    'cyan_fish': 0, 
    'door': 0, 
    'dorrie': 0, 
    'eyerok': 0, 
    'flyguy': 0, 
    'goomba': 0, 
    'heave_ho': 0, 
    'hoot': 0, 
    'king_bobomb': 0, 
    'klepto': 0, 
    'koopa': 7, 
    'koopa_flag': 0, 
    'lakitu_cameraman': 0, 
    'lakitu_enemy': 0, 
    'mad_piano': 0, 
    'manta': 0, 
    'mips': 0, 
    'moneybag': 0, 
    'monty_mole': 0, 
    'peach': 0, 
    'penguin': 0, 
    'piranha_plant': 0, 
    'scuttlebug': 0, 
    'seaweed': 0, 
    'skeeter': 0, 
    'snowman': 0, 
    'spindrift': 0, 
    'spiny': 0, 
    'spiny_egg': 0, 
    'sushi': 0, 
    'swoop': 0, 
    'toad': 0, 
    'ukiki': 0, 
    'unagi': 5, 
    'water_ring': 0, 
    'whomp': 0, 
    'wiggler_body': 0, 
    'wiggler_head': 0, 
    'yoshi': 0 }
    
    
    geo_dict = {}
    geo_source_dict = {}
    
    for each_geo_filepath in geo_filepaths:
        with open( each_geo_filepath, 'r' ) as f:
            geo_txt = remove_if_def( f.read() )
    
        ## Create a dict of geo source code for each struct keyed by struct name.
        geo_structs = geo_txt.split( ';' )
        for each_struct in geo_structs:
            if '=' in each_struct:
                geo_source_dict[ get_name( each_struct ) ] = each_struct
    
    
    ## Read through the geo files again now that we have a source dict to resolve branching.
    for each_geo_filepath in geo_filepaths:
        with open( each_geo_filepath, 'r' ) as f:
            geo_txt = remove_if_def( f.read() )
    
        animation_list = []
        if 'GEO_ANIMATED_PART' in geo_txt:
            ## Find all local animation files.
            skip_stems = [ 'model.inc', 'collision.inc', 'flames_pos.inc', 'geo.inc', 'data.inc' ]
            local_animation_paths = [ i for i in each_geo_filepath.parent.glob( '**/*.c' ) if i.stem not in skip_stems ]
    
            local_anim_source = ''
            for each_path in local_animation_paths:
                with open( each_path, 'r' ) as f:
                    local_anim_source += f.read()
    
            ## Next, we process the animation source.  The goal is to get a list of Animations.
            anim_structs = [ i for i in local_anim_source.split( ';' ) if '=' in i ]
            local_anim_source_dict = {}
            for each_struct in anim_structs:
                assert get_name( each_struct ) != -1, "The animation struct contains no name."
                if 'animindex' in each_struct or 'animvalue' in each_struct or 'Animation' in each_struct:
                    local_anim_source_dict[ get_name( each_struct ) ] = each_struct
    
            ## Pass through the file again and this time look for the pointer to the Animation array.
            for each_struct in anim_structs:
                if 'struct Animation *const' in each_struct:
                    anim_names = read_struct_entries( each_struct )
                    num_anims = len( anim_names )
                    animation_list = [ Animation( anim_name, local_anim_source_dict ) for anim_name in anim_names ]
    
        if animation_list:
            used_animation = animation_list[ animated_objects_dict[ each_geo_filepath.parts[ -2 ] ] ]
        else:
            used_animation = None
    
        geo_structs = geo_txt.split( ';' )
        for each_struct in geo_structs:
            if ' GeoLayout ' in each_struct:
                struct_name = get_name( each_struct )
                geo_dict[ struct_name ] = Geo( struct_name, geo_source_dict, animation=used_animation )
    
    
    
    
    
    with open( mario_graphics_dir / 'model_dicts.pickle' , 'rb' ) as f:
        model_dict, macro_dict, macro_to_geo_dict, special_dict = pickle.load( f )
    
    ## We now have to parse /levels/scripts.c for macro name to geo lookups.
    obj_name_to_geo_dict = {}
    script_filepaths = [ i for i in mario_source_dir.glob( '**/script*.c' ) ]
    for each_script in script_filepaths:
        with open( each_script, 'r' ) as f:
            for line in f:
                if 'LOAD_MODEL_FROM_GEO' in line:
                    obj_name, geo_name = process_line( line )
                    obj_name_to_geo_dict[ obj_name ] = geo_name
                elif 'LOAD_MODEL_FROM_DL' in line:
                    ## Make a new geo object and then put the display list in the geo_dls.
                    name, dl_name, layer = process_line( line )
                    ## TODO: finish this
    
    for each_macro in macro_dict:
        try:
            macro_to_geo_dict[ each_macro ] = obj_name_to_geo_dict[ macro_dict[ each_macro ] ]
            #print( 'Added', each_macro, 'to macro_to_geo_dict.' )
        except:
            pass
            #print( 'COULDN\'T ADD', each_macro, 'TO DICT.' )
    
    special_to_geo_dict = {}
    for each_special in special_dict:
        if 'level_geo' not in each_special:
            try:
                special_to_geo_dict[ each_special ] = obj_name_to_geo_dict[ special_dict[ each_special ] ]
                #print( 'Added', each_special, 'to special_to_geo_dict.' )
            except:
                pass
                #print( 'COULDN\'T ADD', each_special, 'TO DICT.' )
    
    
    obj_to_geo_dict = { **macro_to_geo_dict, **special_to_geo_dict }
    
    obj_name_to_geo_dict = { **obj_to_geo_dict, **obj_name_to_geo_dict }
    
    
    with open( mario_graphics_dir / 'obj_geo_dicts.pickle', 'wb' ) as f:
        pickle.dump( [ obj_name_to_geo_dict, geo_dict ], f, pickle.HIGHEST_PROTOCOL )

    print( "Saved geo dicts to file." )



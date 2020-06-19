from pathlib import Path
import pickle
import copy

from .level_script_parser import process_line


########################
### HELPER FUNCTIONS ###
########################


def remove_comment_from_line( code ):
    """Takes in a line of code as a string and returns the line of code up to any end of line comments."""
    if '//' in code:
        return code[ : code.find( '//' ) ]
    else:
        return code


def get_name( code ):
    """Takes in a block of code corresponding to a struct of either lights, Vtx, or Gfx, and gets the name of the struct."""
    lines = code.split( '\n' )
    for each_line in lines:
        if '//' in each_line:
            each_line = each_line[ : each_line.find( '//' ) ]

        if 'Vtx ' in each_line or 'Gfx ' in each_line:
            if '[]' in each_line:
                temp_line = [ each_word.strip() for each_word in each_line.split( '[]' ) ]
                temp_line = temp_line[ 0 ].split( ' ' )
                return temp_line[ -1 ]

        elif 'Lights1' in each_line:
            temp_line = [ each_word.strip() for each_word in each_line.split( '=' ) ]
            temp_line = temp_line[ 0 ].split( ' ' )
            return temp_line[ -1 ]



###############
### CLASSES ###
###############


class RenderSettings():
    """
    Designed to contain all relevant settings to rendering a particular vertex list.

    Necessary information includes texture, texture settings ( including whether to draw a texture at all ), lighting and lights, combine mode, and geometry mode.
    """
    def __init__( self ):
        self.geometry_mode = { 'G_LIGHTING': True }
        self.combine_mode = []
        self.current_lights = {}
        self.current_texture = None
        self.texture_settings = []
        self.texture_enable = False
        self.texture_render_settings = []
        self.env_colour = None


    def copy( self ):
        copy_object = RenderSettings()
        copy_object.geometry_mode = self.geometry_mode.copy()
        copy_object.combine_mode = self.combine_mode.copy()
        copy_object.current_lights = copy.deepcopy( self.current_lights )
        copy_object.current_texture = self.current_texture
        copy_object.texture_settings = self.texture_settings.copy()
        copy_object.texture_enable = self.texture_enable
        copy_object.texture_render_settings = self.texture_render_settings.copy()
        copy_object.env_colour = self.env_colour
        return copy_object

    def set_combine_mode( self, combine_line ):
        """
        The combine mode settings are a list of length 2.  The values are strings indicating to the Nintendo 64 GPU how to combine colours.  There are two values because of the triple frame buffering.  Generally the two values are identical, but in rare cases, they are different.
        """
        self.combine_mode = process_line( combine_line )

    def set_geometry_mode( self, geometry_line ):
        """
        The geometry mode settings are a string of any length.  Usually the settings are changed one at a time, but this is not always the case.  If more than one are changed, they'll be separated by a | sign.  Typical values for SetGeometryMode are G_FOG, G_LIGHTING, G_CULL_BACK, G_SHADING_SMOOTH.
        """
        geometry_string = process_line( geometry_line )
        geometry_args = [ each_arg.strip() for each_arg in geometry_string.split( '|' ) ]
        for each_arg in geometry_args:
            self.geometry_mode[ each_arg ] = True

    def clear_geometry_mode( self, geometry_line ):
        geometry_string = process_line( geometry_line )
        geometry_args = [ each_arg.strip() for each_arg in geometry_string.split( '|' ) ]
        for each_arg in geometry_args:
            self.geometry_mode[ each_arg ] = False

        if 'G_LIGHTING' in geometry_args:
            self.current_lights = {}

    def set_current_lights( self, light_line, light_dict ):
        """
        There are up to 7 or 8 concurrent lights.  This sets a dictionary with keys equal to index and vals equal to light with the light as a list.  Because only one directional light is used at a time, if the length of the list is 3, it's an ambient light, if it's 6, it's a directional light.
        """
        ## There are a few issues of malformed data in the source code.  In particular, the model.inc.c files for koopa, amp, and bully have a couple of issues.
        try:
            if 'SetLights1' in light_line:
                name = process_line( light_line )
                light = light_dict[ name ]
                self.current_lights[ 1 ] = light.dlights[ 0 ]
                self.current_lights[ 2 ] = light.a

            else:
                name, index = process_line( light_line )
                name = name[ 1 : ] ## Removes the & at the front.
                name, attrib = name.split( '.' )
                light = light_dict[ name ]
                if attrib == 'a':
                    self.current_lights[ index ] = light.a
                elif attrib == 'l':
                    assert len( light.dlights ) == 1, "There are too many lights to assign."
                    self.current_lights[ index ] = light.dlights[ 0 ]

        except:
            pass

    def set_current_texture( self, texture_line ):
        unused1, unused2, unused3, texture_name = process_line( texture_line )
        self.current_texture = texture_name
    
    def load_texture_block( self, temp_line ):
        texture_name, fmt, siz, width, height, pal, cms, cmt, masks, maskt, shifts, shiftt = process_line( temp_line )
        ## Hacky.  There are hex offsets used in some texture names.  This removes the offset and just gets the texture name.
        if ' + ' in texture_name:
            texture_name = texture_name.split()[ 0 ]
        self.current_texture = texture_name
        self.texture_settings = [ fmt, siz, width, 0, 0, pal, cmt, maskt, shiftt, cms, masks, shifts ]

    def set_current_texture_settings( self, texture_settings_line ):
        ## This is set in the SetTile line.
        self.texture_settings = [ each_arg for each_arg in process_line( texture_settings_line ) ]

    def set_current_texture_render( self, texture_render_line ):
        ## This is set in gsSPTexture.
        ## Note: s_size and t_size are in .16 format.  So 0xFFFF = 1, basically.
        s_size, t_size, mipmap_level, tile, texture_enable = process_line( texture_render_line )
        if texture_enable == 'G_ON':
            self.texture_enable = True
        elif texture_enable == 'G_OFF':
            self.texture_enable = False
        self.texture_render_settings = [ s_size, t_size, mipmap_level, tile ]

    def set_env_colour( self, env_colour_line ):
        ## This is set by gsDPSetEnvColor and gives a 4-tuple of RGBA.
        env_r, env_g, env_b, env_a = process_line( env_colour_line )
        self.env_colour = ( env_r, env_g, env_b, env_a )

    def __eq__( self, other ):
        return ( self.geometry_mode == other.geometry_mode and
                 self.combine_mode == other.combine_mode and
                 self.current_lights == other.current_lights and
                 self.current_texture == other.current_texture and
                 self.texture_settings == other.texture_settings and
                 self.texture_render_settings == other.texture_render_settings and
                 self.env_colour == other.env_colour )



class Light():
    """Lights have both ambient and diffuse characteristics.  The first three coordinates of a light are always ambient RGB.  After that, there should be a multiple of 6 values for direction light RGB, and then light position x, y, z.  There may be up to 7 directional lights in a struct.  However, they seem to only use one directional light at a time."""
    def __init__( self, source_str, name ):
        self.name = name
        self.a = [ 0, 0, 0 ]
        self.dlights = []
        self.process_source( source_str )

    def process_source( self, code ):
        try:
            temp = code.replace( '{', '(' )
            temp = code.replace( '}', ')' )
            start = temp.find( '(' )
            end = temp.find( ')' ) + 1
            light_vals = [ each_val for each_val in process_line( code ) ]
            assert len( light_vals ) % 6 == 3, "The light array is the wrong length."
            self.a = light_vals[ : 3 ]
            for i in range( 3, len( light_vals ), 6 ):
                light = light_vals[ i : i + 6 ]
                self.dlights.append( light )

        except:
            ## There are a few strange lights in painting.inc.c files.  They need to be processed differently.
            arr_str = '(' + code[ code.find( '=' ) + 1 : ] + ')'
            arr_str = arr_str.replace( '{', '' )
            arr_str = arr_str.replace( '}', '' )
            arr_str = arr_str.replace( '\n', '' )
            light_vals = [ each_val for each_val in process_line( arr_str ) ]
            assert len( light_vals ) == 20, "The light array doesn't have length 20 either."
            self.a = light_vals[ : 3 ]
            dlight = light_vals[ 8 : 11 ] + light_vals[ 16 : 19 ]
            self.dlights.append( dlight )

    def __eq__( self, other ):
        return ( self.name == other.name and
                 self.a == other.a and
                 self.dlights == other.dlights )


class Vertex():
    """Gets a single vertex from a comma separated string.  Fields are x,y,z, unused bit, tc1 tc2, r,g,b,a.  The game stores vertex normals and vertex colours in the same spot.  So if a vertex is lit, we extract the normal information.  If the vertex is not lit, we extract colour information.  Colours are RGBA."""
    def __init__( self, source_str=None ):
        self.pos = [ 0, 0, 0 ]
        self.tc = [ 0, 0 ]
        self.rgba = [ 0, 0, 0, 0 ]
        if source_str is not None:
            self.process_source( source_str )

    def process_source( self, code ):
        ## Here, cn stands for either a colour or normal coordinate.
        x, y, z, unused, tc1, tc2, cn1, cn2, cn3, cn4 = process_line( code )
        self.pos = [ x, y, z ]
        self.tc = [ tc1, tc2 ]
        self.rgba = [ cn1, cn2, cn3, cn4 ]

    def copy( self ):
        copy_object = Vertex()
        copy_object.pos = self.pos.copy()
        copy_object.tc = self.tc.copy()
        copy_object.rgba = self.rgba.copy()
        return copy_object


class Vtx():
    def __init__( self, source_str=None, name=None, filename=None ):
        """Takes a string at the beginning of the Vtx declaration source code that ends at the end of the Vtx structure."""
        self.filename = filename
        self.name = name
        self.render_settings = None
        self.vertices = []
        self.triangles = []
        if source_str is not None:
            self.get_vertices( source_str )

    def get_vertices( self, code ):

        temp = code.replace( '{{{', '(' )
        temp = temp.replace( '}}}', ')' )
        temp = temp.replace( '{', '' )
        temp = temp.replace( '}', '' )
        
        i = 0
        while i < len( temp ):
            if temp.find( '(', i ) == -1:
                break

            start = temp.find( '(', i )
            end = temp.find( ')', start ) + 1
            self.vertices.append( Vertex( temp[ start : end ] ) )
            i = end


    def add_triangle( self, code_line ):
        """
        Check to see whether the line of code is gsSP2Triangles or gsSP1Triangle.  Use process_line to parse out the triangle data and append to self.triangles.
        """
        triangle_args = process_line( code_line )
        if '2Triangles' in code_line:
            self.triangles += triangle_args[ 0 : 3 ]
            self.triangles += triangle_args[ 4 : 7 ]
        elif '1Triangle' in code_line:
            self.triangles += triangle_args[ 0 : 3 ]


    def copy( self ):
        copy_object = Vtx()
        copy_object.filename = self.filename
        copy_object.name = self.name
        copy_object.render_settings = self.render_settings
        copy_object.vertices = [ vertex.copy() for vertex in self.vertices ]
        copy_object.triangles = self.triangles.copy()
        return copy_object





"""
Takes a string at the beginning of the Gfx declaration source code that ends at the end of the Gfx structure.
Note that there are essentially three kinds of Gfx structs that seem to be used.

-- The first kind are referenced directly by geo files.  These typically start with a gsDPPipeSync() call, followed by gsDPSetCombineMode and GsSPClearGeometryMode calls.  After the environment is set up, texture settings are changed ( such as clamp/mirror/mask/lod/texture size/use texture ), and then other Gfx structures are called with gsSPDisplayList( dl_name ).  At the end of these structures, the CombineMode and GeometryMode are typically set back to a default, usually, ( G_CC_SHADE or G_CC_MODULATERGB ) and G_LIGHTING, respectively.  These can be distinguished from the other two kinds of Gfx because they will call DisplayList.

-- The second kind is rarely seen in levels, but possibly more often seen in objects.  These Gfx can be called to set up environments by changing SetCombineMode and GeometryMode.  These differ from the first kind of Gfx structs in that no DisplayList is called and they are not called from geo.  These will be called from the first kind of Gfx.  These Gfx can be distinguished from the other two kinds of Gfx by the fact that they don't call Vertex nor do they call DisplayList.

-- The final kind of Gfx is what actually does the display.  It usually first sets a texture, then may load lights ( if lighting is enabled ), and finally, load a vertex list and draw triangles.  Note that the vertex lists will look the same regardless of lighting setting, but if lighting is enabled, it reads the colour data instead as normal data.

Each Gfx needs to be parsed differently.  The ultimate goal is to get a list of Vertex/Triangle calls with the texture, texture settings, lights, draw layer, combine mode, and geometry mode.  The draw layer will come from the geo files and are not relevant in this particular parsing.
"""

class Gfx():
    def __init__( self, name, gfx_source_dict, vtx_dict, light_dict ):
        self.render_settings = RenderSettings()
        self.name = name
        #self.gfx_source_dict = gfx_source_dict
        self.vertex_lists = []
        self.process_gfx( self.name, gfx_source_dict, vtx_dict, light_dict )

    def process_gfx( self, name, gfx_source_dict, vtx_dict, light_dict ):
        #print( "Starting in", name )

        lines = gfx_source_dict[ name ]
        curr_line = 0
        while curr_line != len( lines ):

            temp_line = remove_comment_from_line( lines[ curr_line ] )

            if 'BranchList' in temp_line:
                #print( "Branching... Current name =", name, "current line =", curr_line )
                name = process_line( temp_line )
                lines = gfx_source_dict[ name ]
                curr_line = 0


            if 'EndDisplayList' in temp_line:
                #print( "Ending", name )
                return

            elif 'DisplayList' in temp_line:
                new_name = process_line( temp_line )
                #print( "Entering", new_name )
                self.process_gfx( new_name, gfx_source_dict, vtx_dict, light_dict )

            elif 'SetCombineMode' in temp_line:
                self.render_settings.set_combine_mode( temp_line )
                #print( "Set combine mode:", self.render_settings.combine_mode )

            elif 'SetGeometryMode' in temp_line:
                self.render_settings.set_geometry_mode( temp_line )
                #print( "Set geometry:", self.render_settings.geometry_mode )

            elif 'ClearGeometryMode' in temp_line:
                self.render_settings.clear_geometry_mode( temp_line )
                #print( "Cleared geometry:", self.render_settings.geometry_mode )

            elif 'SetTile' in temp_line and 'SetTileSize' not in temp_line:
                self.render_settings.set_current_texture_settings( temp_line )
                #print( "SetTile settings =", self.render_settings.texture_settings )

            ## Possibly use a more general name than gsSPTexture?  Unfortunately, there would be too many collisions with other Texture names.
            elif 'gsSPTexture' in temp_line and 'Rectangle' not in temp_line:
                self.render_settings.set_current_texture_render( temp_line )
                #print( "Texture render set:", self.render_settings.texture_render_settings )
                #print( "Texture enable/disable:", self.render_settings.texture_enable )

            elif 'gsDPLoadTextureBlock' in temp_line:
                self.render_settings.load_texture_block( temp_line )

            elif 'SetTextureImage' in temp_line:
                self.render_settings.set_current_texture( temp_line )
                #print( "Newly set texture =", self.render_settings.current_texture )

            elif 'Light' in temp_line and 'NumLights' not in temp_line:
                self.render_settings.set_current_lights( temp_line, light_dict )
                #print( "Current lights:", self.render_settings.current_lights )

            elif 'Vertex' in temp_line:
                current_vertex_name, num_vertices, vertex_start_ind = process_line( temp_line )
                self.vertex_lists.append( vtx_dict[ current_vertex_name ].copy() )
                ## Assign the current state of render_settings to the render_settings of the vertex.  We need to copy because we will continue changing self.render_settings.
                self.vertex_lists[ -1 ].render_settings = self.render_settings.copy()
                #print( "Set current vertex =", current_vertex_name )

            elif 'Triangle' in temp_line:
                ## Read ahead to see how far triangle calls go, process all of those lines at once, and then advance curr_line the appropriate amount.
                if self.render_settings != self.vertex_lists[ -1 ].render_settings:
                    if len( self.vertex_lists[ -1 ].triangles ) == 0:
                        self.vertex_lists[ -1 ].render_settings = self.render_settings.copy()
                        self.vertex_lists[ -1 ].add_triangle( temp_line )

                    else:
                        ## Get the name of the vertex list in self.vertex_lists[ -1 ]
                        temp_vtx_name = self.vertex_lists[ -1 ].name
                        ## Add a new Vtx to the list that uses the same vertices.
                        self.vertex_lists.append( vtx_dict[ temp_vtx_name ].copy() )
                        ## Copy current render settings.
                        self.vertex_lists[ -1 ].render_settings = self.render_settings.copy()
                        self.vertex_lists[ -1 ].add_triangle( temp_line )

                else:
                    ## Read ahead to see how far triangle calls go, process all of those lines at once, and then advance curr_line the appropriate amount.
                    self.vertex_lists[ -1 ].add_triangle( temp_line )
                    while 'Triangle' in lines[ curr_line + 1 ]:
                        curr_line += 1
                        temp_line = remove_comment_from_line( lines[ curr_line ] )
                        self.vertex_lists[ -1 ].add_triangle( temp_line )
                    #print( "Triangles added:", self.vertex_lists[ -1 ].triangles )

            elif 'SetEnvColor' in temp_line:
                self.render_settings.set_env_colour( temp_line )


            curr_line += 1


class GfxDrawList():
    def __init__( self, name, render_settings, triangles, positions, texel_coordinates, colours ):
        self.name = name
        self.render_settings = render_settings
        self.triangles = triangles
        self.positions = positions
        self.texel_coordinates = texel_coordinates
        self.colors = colours
                    
    def copy( self ):
        copy_triangles = self.triangles.copy()
        copy_positions = self.positions.copy()
        copy_texel_coordinates = self.texel_coordinates.copy()
        copy_colors = self.colors.copy()
        copy_render_settings = self.render_settings.copy()
        copy_object = GfxDrawList( self.name, copy_render_settings, copy_triangles, copy_positions, copy_texel_coordinates, copy_colors )
        return copy_object





############
### MAIN ###
############


def make_vtx_and_gfx_and_light_dict( mario_source_dir, mario_graphics_dir ):
    filelist = [ each_path for each_path in mario_source_dir.glob( '**/model.inc.c' ) ]
    filelist += [ each_path for each_path in mario_source_dir.glob( '**/1.inc.c' ) ]
    filelist += [ each_path for each_path in mario_source_dir.glob( '**/2.inc.c' ) ]
    filelist += [ each_path for each_path in mario_source_dir.glob( '**/3.inc.c' ) ]
    filelist += [ each_path for each_path in mario_source_dir.glob( '**/painting.inc.c' ) ]
    filelist += [ each_path for each_path in mario_source_dir.glob( '**/movtext.inc.c' ) ]
    filelist += [ each_path for each_path in mario_source_dir.glob( '**/anim_*.inc.c' ) ]
    filelist += [ each_path for each_path in ( mario_source_dir / 'levels' ).glob( '**/leveldata.c' ) ]

    with open( mario_graphics_dir / 'gfxs_called_from_geo.pickle', 'rb' ) as f:
        gfxs_called_from_geo = pickle.load( f )

    with open( mario_graphics_dir / 'gfxs_called_from_paintings.pickle', 'rb' ) as f:
        gfxs_called_from_paintings = pickle.load( f )

    vtx_dict = {}
    gfx_dict = {}
    gfx_source_dict = {}
    gfx_display_dict = {}
    light_dict = {}

    light_files = [ each_path for each_path in mario_source_dir.glob( '**/light.inc.c' ) ]
    ## Process light files first to build the light_dict.
    for filename in light_files:
        with open( filename, 'r' ) as f:
            source = f.read()

        source = source.split( ';' )
    
        for each_struct in source:
            ## Read through the data once and skip Gfx structs.
            name = get_name( each_struct )
            if name:
                name_end_ind = each_struct.find( name ) + len( name )

            if 'DefLights' in each_struct:
                light_dict[ name ] = Light( each_struct[ name_end_ind : ], name )
    
    
    ## Process the files into vtx and gfx objects and populate the vtx and gfx dictionaries.
    for filename in filelist:
        current_file_gfxs = []
        with open( filename, 'r' ) as f:
            source = f.read()
    
        source = source.split( ';' )
    
        for each_struct in source:
            ## Read through the data once and skip Gfx structs.
            name = get_name( each_struct )
            if name:
                name_end_ind = each_struct.find( name ) + len( name )

            if 'Vtx ' in each_struct:
                vtx_dict[ name ] = Vtx( each_struct[ name_end_ind : ], name, filename )
                #print( 'Processed vertex data:', name )
    
            elif 'DefLights' in each_struct:
                light_dict[ name ] = Light( each_struct[ name_end_ind : ], name )
                #print( 'Processed lights data:', name )

            elif 'Gfx ' in each_struct:
                gfx_source_dict[ name ] = [ each_line for each_line in each_struct.split( '\n' ) ]


        ## Read through the data again, but only process Gfx structs if they contain "DisplayList"
        for each_struct in source:
            if 'Gfx ' in each_struct:
                name = get_name( each_struct )
                if gfxs_called_from_geo.get( name, False ):
                    current_file_gfxs.append( Gfx( name, gfx_source_dict, vtx_dict, light_dict ) )

                elif name == 'dl_castle_lobby_wing_cap_light':
                    current_file_gfxs.append( Gfx( name, gfx_source_dict, vtx_dict, light_dict ) )

                elif filename.stem == 'leveldata':
                    current_file_gfxs.append( Gfx( name, gfx_source_dict, vtx_dict, light_dict ) )

                elif gfxs_called_from_paintings.get( name, False ):
                    current_file_gfxs.append( Gfx( name, gfx_source_dict, vtx_dict, light_dict ) )


        ## Next, we simply do some preprocessing to put vertex lists into the right format for OpenGL now.  This is done now so that it doesn't have to be done when the game is running, which would increase level load times.
        for each_gfx in current_file_gfxs:

            gfx_output_list = []
            for vtx in each_gfx.vertex_lists:
                current_triangles = vtx.triangles
                current_names = []
                current_positions = []
                current_texels = []
                current_colours = []
                for i in range( len( vtx.vertices ) ):
                    current_positions += vtx.vertices[ i ].pos
                    current_texels += vtx.vertices[ i ].tc
                    current_colours += vtx.vertices[ i ].rgba

                gfx_output_list.append( GfxDrawList( vtx.name, vtx.render_settings, current_triangles, current_positions, current_texels, current_colours ) )

            gfx_display_dict[ each_gfx.name ] = gfx_output_list


    return vtx_dict, gfx_dict, light_dict, gfx_display_dict



def main( mario_source_dir, mario_graphics_dir ):

    vtx_dict, gfx_dict, light_dict, gfx_display_dict = make_vtx_and_gfx_and_light_dict( mario_source_dir, mario_graphics_dir )

    with open( mario_graphics_dir / 'draw_dicts.pickle', 'wb' ) as f:
        pickle.dump( [ vtx_dict, gfx_dict, light_dict, gfx_display_dict ], f, pickle.HIGHEST_PROTOCOL )

    print( "Saved draw dicts to file." )


